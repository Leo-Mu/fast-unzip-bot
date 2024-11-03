import requests
from io import IOBase, SEEK_SET, SEEK_CUR, SEEK_END
import os
from urllib.parse import urlparse

class HTTPRangeFile(IOBase):
    """
    将 HTTP(S) URL 包装成一个类似于 open(file, 'rb') 返回的文件对象
    支持随机读取和迭代
    """
    def __init__(self, url, block_size=8192, filename=None):
        """
        初始化文件对象
        
        Args:
            url: 支持断点续传的文件URL
            block_size: 读取块大小(字节)，默认8KB
            filename: 可选的文件名，如果不提供则从URL中提取
        """
        self.url = url
        self.block_size = block_size
        self.pos = 0
        self._buffer = b""
        self._buffer_start = 0
        
        # 检查URL是否支持Range请求并获取文件信息
        head = requests.head(url, allow_redirects=True)  # 添加 allow_redirects=True
        if 'accept-ranges' not in head.headers:
            raise ValueError("URL does not support range requests")
            
        # 保存完整的头信息
        self._headers = dict(head.headers)
        self.size = int(head.headers['content-length'])

        self._check_range_support()
        
        # 设置文件名
        if filename is not None:
            self.name = filename
        else:
            # 尝试从 Content-Disposition 获取文件名
            cd = head.headers.get('content-disposition')
            if cd and 'filename=' in cd:
                self.name = cd.split('filename=')[-1].strip('"\'')
            else:
                # 从 URL 路径中提取文件名
                path = urlparse(url).path
                self.name = os.path.basename(path) or 'download'
        
        # 用于迭代的会话
        self._session = None
        self._iterator = None
        
        # 模拟文件对象的基本属性
        self.mode = 'rb'
        
        # 缓存常用属性
        self._content_type = head.headers.get('content-type', 'application/octet-stream')

    def _check_range_support(self):
        """验证服务器是否真正支持Range请求"""
        try:
            r = requests.get(self.url, headers={'Range': 'bytes=0-0'})
            if r.status_code != 206:  # 206 Partial Content
                raise ValueError("Server does not properly support range requests")
        except requests.RequestException as e:
            raise ValueError(f"Failed to verify range support: {e}")

    def seek(self, offset, whence=SEEK_SET):
        """
        移动文件指针位置，与标准文件对象行为一致
        """
        if whence == SEEK_SET:
            if offset < 0:
                raise ValueError("Negative seek position")
            new_pos = offset
        elif whence == SEEK_CUR:
            new_pos = self.pos + offset
        elif whence == SEEK_END:
            new_pos = self.size + offset
        else:
            raise ValueError("Invalid whence value")

        if new_pos < 0:
            new_pos = 0
        elif new_pos > self.size:
            new_pos = self.size

        # 如果正在迭代，重置迭代器
        if new_pos != self.pos and self._iterator is not None:
            self._reset_iterator()

        # 清除不再有效的缓冲区
        if not (self._buffer_start <= new_pos < self._buffer_start + len(self._buffer)):
            self._buffer = b""
            self._buffer_start = new_pos

        self.pos = new_pos
        return self.pos

    def tell(self):
        """返回当前文件指针位置"""
        return self.pos

    def read(self, size=-1):
        """
        从当前位置读取指定大小的数据，与标准文件对象行为一致
        """
        # 重置迭代器（如果存在）
        self._reset_iterator()

        if size < 0:
            size = self.size - self.pos
            
        if self.pos >= self.size:
            return b''

        # 使用缓冲区中的数据
        if self._buffer and self._buffer_start <= self.pos < self._buffer_start + len(self._buffer):
            buffer_offset = self.pos - self._buffer_start
            available = len(self._buffer) - buffer_offset
            if available >= size:
                data = self._buffer[buffer_offset:buffer_offset + size]
                self.pos += size
                return data
            data = self._buffer[buffer_offset:]
            self.pos += available
            size -= available
        else:
            data = b''

        # 读取剩余需要的数据
        while size > 0 and self.pos < self.size:
            chunk_size = min(max(size, self.block_size), self.size - self.pos)
            end = min(self.pos + chunk_size - 1, self.size - 1)
            
            headers = {'Range': f'bytes={self.pos}-{end}'}
            try:
                r = requests.get(self.url, headers=headers)
                if r.status_code != 206:
                    raise ValueError("Failed to get partial content")
                chunk = r.content
            except requests.RequestException as e:
                raise IOError(f"Failed to read data: {e}")
                
            self._buffer = chunk
            self._buffer_start = self.pos
            data += chunk
            self.pos += len(chunk)
            size -= len(chunk)
            
        return data

    def _reset_iterator(self):
        """重置迭代器状态"""
        if self._session:
            self._session.close()
            self._session = None
        self._iterator = None

    def readable(self):
        return True

    def seekable(self):
        return True

    def __iter__(self):
        """
        实现迭代器接口，与标准文件对象行为一致
        每次迭代返回一个数据块
        """
        self._reset_iterator()
        self._session = requests.Session()
        headers = {'Range': f'bytes={self.pos}-'}
        response = self._session.get(self.url, headers=headers, stream=True)
        
        if response.status_code != 206:
            raise ValueError("Failed to get partial content")
            
        self._iterator = response.iter_content(chunk_size=self.block_size)
        return self

    def __next__(self):
        """获取下一个数据块"""
        if self._iterator is None:
            raise StopIteration
            
        try:
            chunk = next(self._iterator)
            self.pos += len(chunk)
            return chunk
        except StopIteration:
            self._reset_iterator()
            raise

    @property
    def filename(self):
        """兼容性属性，某些库可能通过此属性获取文件名"""
        return self.name

    def fileno(self):
        """
        文件描述符，我们不支持此功能
        某些库可能会调用此方法
        """
        raise OSError("HTTP range file doesn't support fileno()")

    def isatty(self):
        """不是终端设备"""
        return False

    def writable(self):
        """只读文件"""
        return False

    def close(self):
        """关闭文件对象"""
        self._reset_iterator()
        self._buffer = b""

    def __enter__(self):
        """支持 with 语句"""
        if self.closed:
            raise ValueError("I/O operation on closed file")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持 with 语句"""
        self.close()

    @property
    def content_type(self):
        """返回文件的 MIME 类型"""
        return self._content_type
    
    # 添加属性来获取头信息
    @property
    def headers(self):
        """返回原始文件的 HTTP 头信息"""
        return self._headers