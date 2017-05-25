from linkapp.readinglist.wsgi import ReadinglistMicroservice
from linkapp.readinglist.config import ReadinglistConfig

config = ReadinglistConfig()

app = ReadinglistMicroservice(config)