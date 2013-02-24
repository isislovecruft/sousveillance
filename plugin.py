###
# Copyright (c) 2013, Peter Palfrader <peter@palfrader.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import BeautifulSoup
import re
import time
import urllib2

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class Ticket(callbacks.Plugin):
    expireTimeout = 1800
    minDelta = 300

    """Add the help for "@plugin help Ticket" here
    This should describe *how* to use this plugin."""
    def __init__(self, irc):
        self.__parent = super(Ticket, self)
        self.__parent.__init__(irc)

        self.cache = {}

    def _maybeExpire(self, url, ticketnumber):
        if not ticketnumber in self.cache[url]: return
        if self.cache[url][ticketnumber]['expire'] < time.time():
            del self.cache[url][ticketnumber]

    def _getTicketInfo(self, channel, url, ticketnumber):
        response = urllib2.urlopen('%s%s'%(url, ticketnumber))

        data = response.read()

        charset = response.headers.getparam('charset')
        if charset: data = data.decode(charset)

        b = BeautifulSoup.BeautifulSoup(data, convertEntities=BeautifulSoup.BeautifulSoup.HTML_ENTITIES)
        title = b.find('title').contents[0]
        title = re.sub('\s+', ' ', title).strip()

        filt = self.registryValue('filter', channel)
        if filt:
            m = re.match(filt, title)
            if m and len(m.groups()) > 0:
                title = m.group(1)

        return { 'expire': time.time() + self.expireTimeout,
                 'title': title }

    def _printTitle(self, channel, ticketnumber):
        url = self.registryValue('url', channel)
        if not url: return
        if not url in self.cache: self.cache[url] = {}

        self._maybeExpire(url, ticketnumber)
        if not ticketnumber in self.cache[url]:
            self.cache[url][ticketnumber] = self._getTicketInfo(channel, url, ticketnumber)
        if ticketnumber in self.cache[url]:
            if 'last' in self.cache[url][ticketnumber] and \
               self.cache[url][ticketnumber]['last'] >= time.time() - self.minDelta:
                return
            self.cache[url][ticketnumber]['last'] = time.time()
            return '[#%s - %s]'%(ticketnumber, self.cache[url][ticketnumber]['title'])

    def _processLine(self, channel, payload):
        matches = re.findall('(?<!\S)#([0-9]+)(?=[\s,.-;:])', payload)
        for m in matches:
            title = self._printTitle(channel, m)
            if title: yield title

    def doPrivmsg(self, irc, msg):
        if irc.isChannel(msg.args[0]):
            (channel, payload) = msg.args

            for line in self._processLine(channel, payload):
                irc.queueMsg(ircmsgs.notice(channel, line.encode('utf-8')))
            irc.noReply()


Class = Ticket


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
