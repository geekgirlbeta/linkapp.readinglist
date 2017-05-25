import pika
import json
import strict_rfc3339

import time
import atexit

class TooManyRetries(Exception):
    """
    Link Messenger has tried to reconnect to the message queue too many times.
    """

class ReadinglistMessenger:
    
    def __init__(self, url, max_retries=10, retry_sleep_start=0.1):
        self.url = url
        self.retries = 1
        self.max_retries = max_retries
        self.retry_sleep_start = retry_sleep_start
        
        self.connect()
        atexit.register(self.disconnect)
        
        

        
    def wait(self):
        """
        Returns the next amount of time to wait until retrying a failed 
        operation.
        """
        return self.retry_sleep_start*(self.retries**2)
        
        
    def publish(self, channel, *args, **kwargs):
        try:
            if channel == "job":
                self.job_channel.basic_publish(*args, **kwargs)
            elif channel == "log":
                self.log_channel.basic_publish(*args, **kwargs)
        except pika.exceptions.ConnectionClosed:
            print("Reconnecting")
            self.connect()
            self.publish(channel, *args, **kwargs)

    def connect(self):
        if self.retries >= self.max_retries:
            raise TooManyRetries("Maximum retries of {} exceeded".format(self.retries))
        
        try:
            self.connection = pika.BlockingConnection(pika.URLParameters(self.url))
            
            self.job_channel = self.connection.channel()
            self.job_channel.queue_declare(queue='readinglist_jobs', durable=True)
            
            self.log_channel = self.connection.channel()
            self.log_channel.exchange_declare(exchange='readinglist_logs',type='fanout')
            self.retries = 0
            
        except pika.exceptions.ConnectionClosed:
            print("Reconnecting, waiting {} seconds (retries: {})".format(self.wait(), self.retries))
            time.sleep(self.wait())
            self.retries += 1
            self.connect()
            
    
    def disconnect(self):
        self.connection.close()
    
        
    def job(self, message):
        self.publish("job", 
            exchange='',
            routing_key='readinglist_jobs',
            body=json.dumps(message),
            properties=pika.BasicProperties(
               delivery_mode = 2, # make message persistent
        ))
        
        
        
    def log(self, message):
        message["time"] = strict_rfc3339.now_to_rfc3339_utcoffset()
        
        self.publish("log", 
            exchange='readinglist_logs',
            routing_key='',
            body=json.dumps(message))
        
    
    def viewed_list(self, user):
        message = {
            "user": user,
            "action": "readinglist:viewed"
        }
        
        self.log(message)
    
    def removed_link(self, user, link_id):
        message = {
            "user": user,
            "link_id": link_id,
            "action": "readinglist:removed"
        }
        
        self.log(message)
    
    def added_link(self, user, link_id):
        message = {
            "user": user,
            "link_id": link_id,
            "action": "readinglist:added"
        }
        
        self.log(message)
    
    def read_link(self, user, link_id):
        message = {
            "user": user,
            "link_id": link_id,
            "action": "readinglist:read"
        }
        
        self.log(message)
    
    def unread_link(self, user, link_id):
        message = {
            "user": user,
            "link_id": link_id,
            "action": "readinglist:unread"
        }
        
        self.log(message)
    