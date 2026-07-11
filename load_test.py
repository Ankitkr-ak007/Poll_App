import asyncio
import aiohttp
import time
import sys

async def fetch(session, url):
    async with session.get(url) as response:
        return response.status

async def bound_fetch(sem, session, url):
    async with sem:
        return await fetch(session, url)

async def main(url, concurrent_requests=150):
    print(f"Starting load test against {url} with {concurrent_requests} concurrent requests...")
    
    sem = asyncio.Semaphore(concurrent_requests)
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        # Fire requests concurrently
        tasks = [bound_fetch(sem, session, url) for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
    duration = end_time - start_time
    success_count = sum(1 for r in results if r == 200)
    error_count = len(results) - success_count
    
    print("\n--- Load Test Results ---")
    print(f"Total Requests: {len(results)}")
    print(f"Successful (200 OK): {success_count}")
    print(f"Failed: {error_count}")
    print(f"Time Taken: {duration:.3f} seconds")
    print(f"Requests per second: {len(results)/duration:.2f} req/s")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python load_test.py <API_URL>")
        print("Example: python load_test.py http://localhost:8000/api/results/1234")
        sys.exit(1)
        
    asyncio.run(main(sys.argv[1]))
