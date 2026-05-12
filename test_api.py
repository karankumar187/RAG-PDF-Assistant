import asyncio
import os
from main import sync_ingest
from fastapi import UploadFile
import io
import uuid

async def test():
    file_content = b"fake pdf content"
    file = UploadFile(filename="test.pdf", file=io.BytesIO(file_content))
    res = await sync_ingest(file, "user123")
    print(res)

asyncio.run(test())
