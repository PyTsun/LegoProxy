from time import time
from asyncio import sleep
from datetime import datetime
from json.decoder import JSONDecodeError

from httpx import AsyncClient
from httpx._exceptions import ConnectError, ConnectTimeout, RequestError

from core.conf import LegoProxyConfig

global totalRequests
proxylist = open("assets/proxies.txt", "r").read().split()
totalRequests = 0

async def resetRequestsCounter():
    global totalRequests
    while True:
        await sleep(1)
        totalRequests -= totalRequests

class proxyRequest():
    log = ""
    
    subdomain: str
    path: str
    data: dict
    method: str
    params: str = None

    authRobloxId: int
    authKey: str

    authUserAgent: str

    lastproxy = -1
    cache = {}

    async def request(self, config: LegoProxyConfig):
        global totalRequests
        cacheExpiry = config.expiry

        if config.caching:
            cache_key = (self.subdomain, self.path, tuple(self.data.items()), self.method)
            if cache_key in self.cache:
                cache_entry = self.cache[cache_key]
                if cache_entry["timestamp"] + cacheExpiry > time():
                    return cache_entry["response"]
                else:
                    del self.cache[cache_key]

        if self.subdomain in config.blacklistedSubdomains:
            return {"success": False, "message": "LegoProxy - The Roblox API Subdomain is Blacklisted to this LegoProxy server."}

        if totalRequests > config.maxRequests:
            return {"success": False, "message": "LegoProxy - Requests Overload. Please try again!"}

        if config.placeId != 0 and self.authRobloxId != config.placeId: 
            return {"success": False, "message": "LegoProxy - This proxy is only accepting requests from a Roblox Game."}

        if config.proxyAuthKey != "" and self.authKey != config.proxyAuthKey:
            return {"success": False, "message": "LegoProxy - This proxy requires an Authentication Key."}

        self.lastproxy = (self.lastproxy + 1) % len(proxylist)
        proxy = proxylist[self.lastproxy]

        try:
            async with AsyncClient(proxies={"http://": f"http://{proxy}"}) as cli:
                if self.params == None:
                    req = cli.build_request(self.method, f"https://{self.subdomain}.roblox.com/{self.path}", data=self.data)
                else:
                    req = cli.build_request(self.method, f"https://{self.subdomain}.roblox.com/{self.path}?{self.params}", data=self.data)

                res = await cli.send(req)
                response = res.json()

                t = datetime.now()
                c = t.strftime("%I:%M:%S.%f %p")
                proxyRequest.log = f"<text style='color: rgb(69, 255, 69)'>[ {t.month}/{t.day} @ {c} :: {self.method} ]</text><br><text><text style='color: #75b2eb;'>Lego</text><text style='color: #87d997;'>Proxy</text> --> ({self.subdomain}) {self.path}<br>{response}</text><br>"

        except JSONDecodeError: 
            response = {"success": False, "message": "LegoProxy - Roblox API did not return JSON Data."}

        except ConnectTimeout: 
            response = {"success": False, "message": f"LegoProxy - Connection Timeout. Proxy IP {proxy} could be a dead proxy."}

        except ConnectError: 
            response = {"success": False, "message": "LegoProxy - Roblox API Subdomain does not exist."}
        
        except RequestError:
            response = {"success": False, "message": "LegoProxy - Failed to create a request."}

        totalRequests += 1
        if config.caching: self.cache[cache_key] = {"timestamp": time(), "response": response}
        return response

