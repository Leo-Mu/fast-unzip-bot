import os
import asyncio

class TelethonFileWrapper:
    """将 Telethon document file 包装成本地文件接口，支持断点续传和完整的元数据"""
    def __init__(self, client, file):
        self.client = client
        self.file = file
        
        self.mode = 'rb'
        self.pos = 0
        self._closed = False
        
        self.size = file.size
        self.name = file.attributes[0].file_name
    
    def readable(self):
        return not self._closed
    
    def seekable(self):
        return True
    
    def writable(self):
        return False
    
    def seek(self, offset, whence=os.SEEK_SET):
        if self._closed:
            raise ValueError("I/O operation on closed file")
        if whence == os.SEEK_SET:
            self.pos = offset
        elif whence == os.SEEK_CUR:
            self.pos += offset
        elif whence == os.SEEK_END:
            self.pos = self.size + offset
        self.pos = max(0, min(self.pos, self.size))
        return self.pos
    
    def tell(self):
        if self._closed:
            raise ValueError("I/O operation on closed file")
        return self.pos
    
    async def read(self, size=-1):
        """Asynchronous read method that handles downloading."""
        if self._closed:
            raise ValueError("I/O operation on closed file")
        if size == -1:
            size = self.size - self.pos
        if size == 0 or self.pos >= self.size:
            return b''
        size = min(size, self.size - self.pos)
        
        # Perform the download asynchronously
        data = await self._read_async(size)
        self.pos += len(data)
        return data

    async def _read_async(self, size):
        """Perform the download asynchronously."""
        return b''.join([chunk async for chunk in self.client.iter_download(self.file, offset=self.pos, request_size=size)])
    
    def close(self):
        self._closed = True
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    @property
    def closed(self):
        return self._closed
