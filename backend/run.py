import asyncio
import sys
import warnings

if sys.platform == "win32":
    warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*WindowsSelectorEventLoopPolicy.*")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001)
