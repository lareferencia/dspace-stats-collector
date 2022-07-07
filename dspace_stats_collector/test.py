import re

urls = ['jdbc:postgresql://localhost.com.ar:5432/dspace', 'jdbc:oracle:thin:@//HOST.com.ar:12312/SERVICE', 'jdbc:oracle:thin:@123.122.323:12122:SID']



for jdbcUrl in urls:
    m = re.match("^jdbc:(postgresql|oracle):[^\/|^@]*[@\/\/|\/\/|@]*([^:]+):(\d+)(\/|:)(.*)$", jdbcUrl)
    print( m.group(1, 2, 3, 4, 5) )



