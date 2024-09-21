import base64
import requests
import scrapy
import time
import json
import os
from dotenv import load_dotenv


load_dotenv()


class FreeProxySpider(scrapy.Spider):
    name = "free_proxy"
    allowed_domains = ["free-proxy.cz"]
    start_urls = [f'http://free-proxy.cz/en/proxylist/main/{i}' for i in range(1, 6)]
    token = os.getenv('TOKEN')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()

    def parse(self, response):
        rows = response.css('table#proxy_list tbody tr')
        proxies = []

        for row in rows:
            ip_base64 = row.css('td:nth-child(1) script::text').re_first(r'"([A-Za-z0-9+/=]+)"')
            if ip_base64:
                ip = base64.b64decode(ip_base64).decode('utf-8')

                port = row.css('td:nth-child(2) span.fport::text').get()

                if port:
                    proxy = f"{ip}:{port}"
                    proxies.append(proxy)

        if proxies:
            self.logger.info(f"Parsed {len(proxies)} proxies.")
            form_token = self.get_form_token()
            if form_token:
                self.upload_proxies(proxies, form_token)
            else:
                self.logger.error("Failed to retrieve form token.")

    def get_form_token(self):
        url = 'https://test-rg8.ddns.net/api/get_token'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:130.0) Gecko/20100101 Firefox/130.0'
        }
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                token_data = response.cookies
                return token_data.get('form_token')
            else:
                self.logger.error(f"Error retrieving form_token: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error retrieving form_token: {e}")
        return None

    def upload_proxies(self, proxies, form_token):
        url = 'https://test-rg8.ddns.net/api/post_proxies'
        cookies = {'form_token': form_token,
                   'x-user_id': self.token}
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://test-rg8.ddns.net',
            'Referer': 'https://test-rg8.ddns.net/task',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:130.0) Gecko/20100101 Firefox/130.0'
        }

        proxies_str = ', '.join(proxies)
        data = json.dumps({
            "user_id": self.token,
            "len": len(proxies),
            "proxies": proxies_str
        })
        try:
            time.sleep(30)
            response = requests.post(url, headers=headers, cookies=cookies, data=data)
            if response.status_code == 200:
                save_id = response.json().get('save_id')
                if save_id:
                    self.save_results(save_id, proxies)
                else:
                    self.logger.error("save_id not found in response.")
            else:
                self.logger.error(f"Error uploading proxies: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error uploading proxies: {e}")

    def save_results(self, save_id, proxies):
        results = {}
        try:
            with open('results.json', 'r') as f:
                results = json.load(f)
        except FileNotFoundError:
            pass

        results[save_id] = proxies

        with open('results.json', 'w') as f:
            json.dump(results, f, indent=4)

        self.logger.info(f"Proxies uploaded and saved with save_id {save_id}")

    def closed(self, reason):
        execution_time = time.time() - self.start_time
        time_str = time.strftime('%H:%M:%S', time.gmtime(execution_time))

        with open('time.txt', 'w') as f:
            f.write(time_str)

        self.logger.info(f"Execution time: {time_str}")
