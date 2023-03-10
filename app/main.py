from fastapi import FastAPI, Request, Response, status, HTTPException
import redis 
from pydantic import BaseModel
import time

app = FastAPI()

cache = redis.Redis(host='redis', port=6379, decode_responses=True)

class RateLimiter(BaseModel):
    request_per_second: int
    endpoint: str


def get_endpoints(request):
    return [route.path for route in request.app.routes]

def get_cache(endpoint, client):
    current_timestamp = int(time.time())
    res = cache.hgetall(client)
    if res:
        rps =  cache.get(endpoint)
        print(res)
        last_timestamp = int(res['last_timestamp'])
        count = res['count']
        time_from_last_request = current_timestamp - last_timestamp
        cache.hmset(client, {
                'last_timestamp': current_timestamp,
                'count':  int(count)+1
        })
        cache.expire(client,1)
        if count > rps*time_from_last_request:
            return False
    else:
        cache.hmset(client,{
            'last_timestamp': current_timestamp,
            'count': 1
        })
        cache.expire(client,1)
    return True

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/ratelimiter", status_code=status.HTTP_200_OK)
def set_rate_limiter(request: Request, data: RateLimiter):
    url_lists = get_endpoints(request)
    if data.endpoint not in url_lists:
        raise HTTPException(status_code=400, detail='Invalid API endpoint')
    cache.set(data.endpoint, data.request_per_second)
    return {
        "message": f'API endpoint {data.endpoint} is configured with ratelimiter successfully'
    }



@app.get("/items", status_code=status.HTTP_200_OK)
def read_item(request: Request, response: Response):
    client_host = request.client.host
    res = get_cache("/items", client_host)
    if not res:
        raise HTTPException(status_code=429, detail="API throttle")
    return {
            "message": "return item"
    }
