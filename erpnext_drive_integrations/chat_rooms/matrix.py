"""The few calls the business system's bot makes to the chat server (P73). No Frappe here.

The bot signs in with its own token (an application service registration on the chat server) and uses only the
ordinary client interface: find a room by its address, create it, read its members, invite, remove, post. It
holds no admin right. No token value is ever put into an error or a log line.
"""
import json
import urllib.parse


class ChatError(Exception):
    """The chat server refused or could not be reached; the message never contains a credential."""

    def __init__(self, message, status=None, code=None):
        super().__init__(message)
        self.status, self.code = status, code


class Bot:
    def __init__(self, url, server_name, token, send=None, timeout=20):
        if not (url and server_name and token):
            raise ChatError('The chat connection is not set up.')
        self.url, self.server, self._token, self.timeout = url.rstrip('/'), server_name, token, timeout
        self._send = send or self._requests
        self.user_id = '@erp:' + server_name

    def _requests(self, method, url, headers, body, timeout):
        import requests
        try:
            answer = requests.request(method, url, headers=headers, data=body, timeout=timeout)
        except requests.RequestException:
            raise ChatError('The chat server could not be reached.')
        return answer.status_code, answer.content

    def call(self, method, path, body=None, missing_ok=False):
        headers = {'Authorization': 'Bearer ' + self._token}
        data = None
        if body is not None:
            data, headers['Content-Type'] = json.dumps(body).encode(), 'application/json'
        status, content = self._send(method, self.url + path, headers, data, self.timeout)
        try:
            answer = json.loads(content or b'{}')
        except ValueError:
            answer = {}
        if status == 404 and missing_ok:
            return None
        if status >= 400:
            raise ChatError('The chat server answered %s (%s).' % (status, answer.get('errcode') or 'no code'),
                            status, answer.get('errcode'))
        return answer

    def full_alias(self, alias):
        return '#%s:%s' % (alias, self.server)

    def room_id(self, alias):
        answer = self.call('GET', '/_matrix/client/v3/directory/room/' + urllib.parse.quote(self.full_alias(alias)),
                           missing_ok=True)
        return answer and answer.get('room_id')

    def create_room(self, alias, name, topic, levels, invite=()):
        return self.call('POST', '/_matrix/client/v3/createRoom', {
            'room_alias_name': alias, 'name': name, 'topic': topic, 'preset': 'private_chat',
            'power_level_content_override': dict(levels), 'invite': list(invite)})['room_id']

    def _room(self, room_id, rest):
        return '/_matrix/client/v3/rooms/%s%s' % (urllib.parse.quote(room_id), rest)

    def states(self, room_id):
        """Everyone joined or invited, as {user ID: 'join' or 'invite'}."""
        answer = self.call('GET', self._room(room_id, '/members'))
        return {event['state_key']: event['content']['membership'] for event in answer.get('chunk', [])
                if event.get('content', {}).get('membership') in ('join', 'invite')}

    def members(self, room_id):
        return sorted(self.states(room_id))

    def exists(self, user_id):
        """Whether this person has a chat account yet (it is made at their first sign-in)."""
        return self.call('GET', '/_matrix/client/v3/profile/' + urllib.parse.quote(user_id), missing_ok=True) is not None

    def invite(self, room_id, user_id):
        self.call('POST', self._room(room_id, '/invite'), {'user_id': user_id})

    def remove(self, room_id, user_id, reason):
        self.call('POST', self._room(room_id, '/kick'), {'user_id': user_id, 'reason': reason})

    def name(self, room_id):
        answer = self.call('GET', self._room(room_id, '/state/m.room.name'), missing_ok=True)
        return (answer or {}).get('name')

    def rename(self, room_id, name):
        self.call('PUT', self._room(room_id, '/state/m.room.name'), {'name': name})

    def post(self, room_id, key, text, notice=False):
        """`key` makes a repeat harmless: the chat server keeps one message per key."""
        self.call('PUT', self._room(room_id, '/send/m.room.message/' + urllib.parse.quote(key, safe='')),
                  {'msgtype': 'm.notice' if notice else 'm.text', 'body': text})
