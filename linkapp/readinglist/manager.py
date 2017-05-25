import redis
import strict_rfc3339

from .queue import ReadinglistMessenger

from .wrapper import ServiceWrapper, NotFound

class UserNotFound(Exception):
    """
    Raised when a user cannot be found.
    """
    
class LinkNotFound(Exception):
    """
    Raised when a link_id cannot be found.
    """

class ReadinglistManager:
    
    def __init__(self, redis_url="redis://localhost:6379/0", 
                       rabbit_url="amqp://localhost"):
        self.connection = redis.StrictRedis.from_url(redis_url, decode_responses=True)
        self.readinglist_messenger = ReadinglistMessenger(rabbit_url)
    
    def key(self, user):
        return "list:{}".format(user)
        
    def key_read(self, user):
        return "list-read:{}".format(user)
        
    def add(self, user, link_id):
        score = float(strict_rfc3339.rfc3339_to_timestamp(strict_rfc3339.now_to_rfc3339_utcoffset()))
        
        with self.connection.pipeline() as pipe:
            pipe.zadd(self.key(user), score, link_id)
            pipe.srem(self.key_read(user), link_id)
            
            pipe.execute()
            
        self.readinglist_messenger.added_link(user, link_id)
    
    def remove(self, user, link_id):
        with self.connection.pipeline() as pipe:
            pipe.srem(self.key_read(user), link_id)
            pipe.zrem(self.key(user), link_id)
        
            pipe.execute()
            
        self.readinglist_messenger.removed_link(user, link_id)
    
    def read(self, user, link_id):
        self.connection.sadd(self.key_read(user), link_id)
        
        self.readinglist_messenger.read_link(user, link_id)
    
    def unread(self, user, link_id):
        self.connection.srem(self.key_read(user), link_id)
        
        self.readinglist_messenger.unread_link(user, link_id)
    
    def to_read(self, user):
        key = self.key(user)
        key_read = self.key_read(user)
        
        with self.connection.pipeline() as pipe:
            temp_key = "to-read:{}:temp".format(user)
            pipe.zunionstore(temp_key, {key:1, key_read:0}, "MIN")
            pipe.zrangebyscore(temp_key, 1, "+inf")
            
            pipe.delete(temp_key)
            
            result = pipe.execute()
        
        self.readinglist_messenger.viewed_list(user)
        
        return result[1]
    
    def already_read(self, user):
        key = self.key(user)
        key_read = self.key_read(user)
        
        with self.connection.pipeline() as pipe: 
            temp_key = "been-read:{}:temp".format(user)
            pipe.zunionstore(temp_key, {key:0, key_read:1}, "MIN")
            pipe.zrangebyscore(temp_key, 1, "+inf")
            
            pipe.delete(temp_key)
            
            result = pipe.execute()
            
        return result[1]
        