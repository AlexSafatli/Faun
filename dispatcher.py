# dispatch.py
# -------------------------
# Winter 2013; Alex Safatli
# -------------------------
# An IMAP message request/response 
# protocol API for use with the 
# faun mail client.

import os  

# Protocol literals.

name = 'IMAP'         # Protocol name.
version = '4rev1'     # Protocol version.
port = 143            # Protocol port.
commands =         ['CAPABILITY','NOOP','LOGOUT','STARTTLS',\
                     'AUTHENTICATE','LOGIN','SELECT','EXAMINE',\
                     'CREATE','DELETE','RENAME','SUBSCRIBE',\
                     'UNSUBSCRIBE','LIST','LSUB','STATUS',\
                     'APPEND','CHECK','CLOSE','EXPUNGE',\
                     'SEARCH','FETCH','STORE','COPY','UID']

# Dispatcher; handles the receiving and sending
# of all messages, incl. error management.

class dispatcher:
    def __init__(self,hostname,socket,tag):
        self.hostname = hostname
        self.socket = socket
        self.tag = tag
        self.history = {} # stores all messages sent by their tag
    def receiveData(self):
        # Receive a message from
        # a socket. Receives 1 bit 
        # at a time.
        sock = self.socket
        try:
            data = sock.recv(1)
        except:
            return None
        # Got first 1 bit of information.
        # Now keep taking 1 out until full
        # message received.
        bit = data
        while bit:
            bit = sock.recv(1)
            data += bit
            if (data[-2:] == '\r\n'):
                # now at end of line
                break
        return data
    def __sndrcv__(self,req=None):
        sock = self.socket
        if req and req.result:
            req.tag = self.tag # append tag
            sock.send(str(req))
            data = self.receiveData()
            if not data:
                print 'Connection closed by user or server.'
                sock.close()
                exit()
            r = response(data,self.tag.tag)
            while (r.status == 2):
                r.new(self.__sndrcv__())
            return r
        elif not req:
            data = self.receiveData()
            if not data:
                print 'Connection closed by user or server.'
                sock.close()
                exit()
            return data
        else:
            return None
    def sendMessage(self,req,ex=True):
        resp = self.__sndrcv__(req)
        if resp and resp.status < 0:
            # if not succesful
            print 'Could not perform %s (%s).' % (req.op,resp.desc)
            if ex:
                exit()
        elif not resp:
            raise SystemError('Message reconstruction from socket failed.')
        # add message to dispatcher history
        self.history[req.tag.tag] = req
        return resp
    def rawSend(self,data):
        sock = self.socket
        sock.send(data)
        sock.send('\r\n\r\n')
        data = self.receiveData()

        if not data:
            print 'Connection closed by user or server.'
            sock.close()
            exit()
        r = response(data,self.tag.tag)
        return r

# Tag management; handles preceding identifier
# for IMAP communication.

class tag:
    def __init__(self):
        self.seed = 0
        self.tag = 'a000'
    def next(self):
        self.seed += 1
        self.tag = 'a%.3d' % (self.seed)
        return self.tag

# Server response management.

class response:
    def __init__(self,strn,reqtag):
        self.reqtag = reqtag
        self.string = strn
        self.status = -1
        self.buffer = [] # for multiple * messages
        self.__iden__()
    def new(self,strn):
        self.buffer.append(self.desc)
        self.string = strn
        self.__iden__()
    def parseMailboxes(self):
        out = []
        for f in self.buffer:
            l = f.split()
            out.append(l[-1].strip('"'))
        return out
    def __iden__(self):
        strn = self.string
        if strn.startswith('+'):
            # server waiting on next response
            self.status = 1
            self.desc = self.string[1:].strip()
        elif strn.startswith('*'):
            # information response
            self.status = 2
            self.desc = self.string[1:].strip()
        elif strn.startswith(self.reqtag):
            l = strn.split()
            if len(l) > 1 and l[1] == 'OK':
                self.status = 0
            if len(l) > 2:
                self.desc = ' '.join(l[2:])       
            else:
                self.desc = self.string
        else:
            self.status = 2
            self.desc = self.string
        self.desc = self.desc.strip('\r\n')        
            

# Client request management.

class request:
    def __init__(self,command,*args):
        self.tag = None
        self.op = command
        self.args = args
        if self.op.upper() in commands:
            # Valid operation.
            self.result = self.go()
        else:
            self.result = None
    def go(self):
        out = '%s ' % (self.op)
        for item in self.args:
            out += '%s ' % (item)
        return out[:-1]
    def __str__(self):
        return '%s %s\r\n' % (self.tag.next(),self.result)
