"""
/[user]                     GET         reading list
/[user]                     POST        add a link to the reading list
/[user]/[link_id]           DELETE      remove link from list
/[user]/[link_id]/read      PUT         mark a link as read
/[user]/[link_id]/unread    PUT         mark a link as unread
"""

from webob import Response, Request

from .manager import ReadinglistManager, UserNotFound, LinkNotFound
from .queue import ReadinglistMessenger
import base64

def bad_request(environ, start_response, msg="Bad Request", status=400):
    res = Response(msg, status=status)
    
    return res(environ, start_response)

class BadRequest(Exception):
    """
    Raised when something bad happened in a request
    """
    
    def __init__(self, msg="Bad Request", code=400):
        self.msg = msg
        self.code = code
        
    def __str__(self):
        return self.msg
        
        
    def __call__(self, environ, start_response):
        res = Response(self.msg, status=self.code)
        return res(environ, start_response)
    
class NotFound(BadRequest):
    """
    Raised when something is not found.
    """
    def __init__(self, msg="Not Found", code=404):
        BadRequest.__init__(self, msg, code)
    
class UnsupportedMediaType(BadRequest):
    """
    Raised when a bad content type is specified by the client.
    """
    def __init__(self, msg="Unsupported media type", code=415):
        BadRequest.__init__(self, msg, code)
        

class ReadinglistMicroservice:
    
    def __init__(self, config):
        self.config = config
        
        self.readinglist_manager = ReadinglistManager(
            self.config.redis_url, 
            self.config.rabbit_url)
        
        self.readinglist_messenger = ReadinglistMessenger(self.config.rabbit_url)
    
    def __call__(self, environ, start_response):
        req = Request(environ)
        
        parts = req.path.split("/")[1:]
        
        try:
            if req.content_type != "application/json":
                raise UnsupportedMediaType()
                
            if len(parts) == 1:
                username = parts[0]
                
                if req.method == 'GET':
                    result = self.get_readinglist(req, username)
                elif req.method == 'POST':
                    result = self.add_link(req, username)
                else:
                    raise BadRequest()
            elif len(parts) == 2:
                username = parts[0]
                link_id = parts[1]
                
                if req.method == 'DELETE':
                    result = self.remove_link(req, username, link_id)
                else:
                    raise BadRequest()
            elif len(parts) == 3:
                username = parts[0]
                link_id = parts[1]
                action = parts[2]
                
                if req.method == 'PUT':
                    if action == 'read':
                        result = self.read_link(req, username, link_id)
                    elif action == 'unread':
                        result = self.unread_link(req, username, link_id)
                    else:
                        raise BadRequest()
                else:
                    raise BadRequest()
        except BadRequest as br:
            return br(environ, start_response)
        except UserNotFound:
            res = NotFound("User not found")
            return res(environ, start_response)
        except LinkNotFound:
            res = NotFound("Link not found")
            return res(environ, start_response)
        except ValueError as e:
            return bad_request(environ, start_response, str(e))
            
        res = Response()
        res.json = result
        return res(environ, start_response)
        
        
    def get_readinglist(self, req, username):
        return self.readinglist_manager.to_read(username)
    
    def add_link(self, req, username):
        link_id = req.json
        return self.readinglist_manager.add(username, link_id)
    
    def remove_link(self, req, username, link_id):
        return self.readinglist_manager.remove(username, link_id)
    
    def read_link(self, req, username, link_id):
        return self.readinglist_manager.read(username, link_id)
    
    def unread_link(self, req, username, link_id):
        return self.readinglist_manager.unread(username, link_id)