import requests
from io import BytesIO
import os
import time
import mimetypes
import urllib.parse
from datetime import datetime
import stat

class HTTPFileWrapper:
    """将 HTTP URL 包装成本地文件接口，支持断点续传和完整的元数据"""
    
    def __init__(self, url, block_size=8192):
        """
        初始化文件包装器
        
        Args:
            url: HTTP URL
            block_size: 数据块大小，用于分块下载
        """
        self.url = url
        self.block_size = block_size
        self.pos = 0
        self.cache = BytesIO()
        self._closed = False
        
        # 获取文件信息和元数据
        response = requests.head(url, allow_redirects=True)
        response.raise_for_status()
        
        # 基本属性
        self.size = int(response.headers.get('content-length', 0))
        self.resumable = 'bytes' in response.headers.get('accept-ranges', '')
        
        # 解析并存储元数据
        self._parse_metadata(response.headers)
        
        # 文件模式（模拟只读文件）
        self.mode = 'rb'
    
    def _parse_metadata(self, headers):
        """解析 HTTP 头中的元数据"""
        # 文件名
        if 'content-disposition' in headers:
            import re
            pattern = r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)'
            matches = re.findall(pattern, headers['content-disposition'])
            if matches:
                self.name = matches[0][0].strip('"\'')
            else:
                self.name = urllib.parse.unquote(self.url.split('/')[-1])
        else:
            self.name = urllib.parse.unquote(self.url.split('/')[-1])
        
        # 修改时间
        if 'last-modified' in headers:
            self.mtime = time.mktime(datetime.strptime(
                headers['last-modified'],
                '%a, %d %b %Y %H:%M:%S %Z'
            ).timetuple())
        else:
            self.mtime = time.time()
        
        # 创建时间（通常无法获取，使用修改时间）
        self.ctime = self.mtime
        
        # 访问时间（当前时间）
        self.atime = time.time()
        
        # MIME 类型
        if 'content-type' in headers:
            self.content_type = headers['content-type'].split(';')[0]
        else:
            self.content_type = mimetypes.guess_type(self.name)[0] or 'application/octet-stream'
        
        # 文件属性
        self._build_stat()
    
    def _build_stat(self):
        """构建类似 os.stat 的属性结构"""
        self.stat_result = os.stat_result((
            # st_mode (文件模式，设置为普通只读文件)
            stat.S_IFREG | 0o444,
            # st_ino (inode 数量，设为0)
            0,
            # st_dev (设备 ID，设为0)
            0,
            # st_nlink (硬链接数，设为1)
            1,
            # st_uid (用户 ID，设为当前用户)
            os.getuid(),
            # st_gid (组 ID，设为当前组)
            os.getgid(),
            # st_size (文件大小)
            self.size,
            # st_atime (访问时间)
            self.atime,
            # st_mtime (修改时间)
            self.mtime,
            # st_ctime (创建时间)
            self.ctime
        ))
    
    def fileno(self):
        """
        返回文件描述符（这里抛出异常因为没有真实的文件描述符）
        """
        raise IOError("HTTP file wrapper does not have a real file descriptor")
    
    def isatty(self):
        """
        判断文件是否是一个终端设备
        """
        return False
    
    def readable(self):
        """
        判断文件是否可读
        """
        return not self._closed
    
    def seekable(self):
        """
        判断文件是否可定位
        """
        return True
    
    def writable(self):
        """
        判断文件是否可写
        """
        return False
    
    def seek(self, offset, whence=os.SEEK_SET):
        """实现文件 seek 操作"""
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
        """返回当前文件位置"""
        if self._closed:
            raise ValueError("I/O operation on closed file")
        return self.pos
    
    def read(self, size=-1):
        """读取指定大小的数据"""
        if self._closed:
            raise ValueError("I/O operation on closed file")
            
        if size == -1:
            size = self.size - self.pos
            
        if size == 0 or self.pos >= self.size:
            return b''
            
        size = min(size, self.size - self.pos)
        
        headers = {'Range': f'bytes={self.pos}-{self.pos + size - 1}'}
        response = requests.get(self.url, headers=headers)
        
        if response.status_code in (200, 206):
            data = response.content
            self.pos += len(data)
            # 更新访问时间
            self.atime = time.time()
            self._build_stat()
            return data
        else:
            raise IOError(f"Failed to read data: HTTP {response.status_code}")
    
    def close(self):
        """关闭文件"""
        self._closed = True
    
    def __enter__(self):
        """支持 with 语句"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """清理资源"""
        self.close()
    
    @property
    def closed(self):
        """返回文件是否已关闭"""
        return self._closed
    
    def __getattr__(self, name):
        """支持通过 stat 属性访问文件元数据"""
        if name.startswith('st_'):
            return getattr(self.stat_result, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")