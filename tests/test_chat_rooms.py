"""Chat rooms follow the sites (P73): the rules, the bot's calls and the run that applies them.

Offline. The rules and the bot's client have no Frappe in them and run for real; the applying run uses a chat
server kept in memory and a minimal stand-in for Frappe. The live part is the run against the test chat server.
"""
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FRAPPE = sys.modules.setdefault('frappe', types.ModuleType('frappe'))
if not hasattr(FRAPPE, 'conf'):
    FRAPPE.conf = {}
from erpnext_drive_integrations.chat_rooms import rules, sync  # noqa: E402
from erpnext_drive_integrations.chat_rooms.matrix import Bot, ChatError  # noqa: E402

SERVER = 'chat.example.net'
NAMES = {'sup@example.net': 'asha.k', 'eng@example.net': 'ravi.m', 'pm@example.net': 'meena.s',
         'staff@example.net': 'john.d', 'other-sup@example.net': 'lata.p', 'nameless@example.net': None}
SITE = {'name': 'North Yard / Phase 2', 'label': 'North Yard', 'enabled': True,
        'labels': {'sup@example.net': 'Asha K', 'other-sup@example.net': 'Lata P'},
        'members': [
            {'user': 'sup@example.net', 'team_role': 'Supervisor', 'enabled': True, 'verifier': 'eng@example.net'},
            {'user': 'other-sup@example.net', 'team_role': 'Supervisor', 'enabled': True, 'verifier': None},
            {'user': 'eng@example.net', 'team_role': 'Verifier', 'enabled': True, 'verifier': None},
            {'user': 'pm@example.net', 'team_role': 'Approver', 'enabled': True, 'verifier': None},
            {'user': 'staff@example.net', 'team_role': 'Staff', 'enabled': False, 'verifier': None},
            {'user': 'nameless@example.net', 'team_role': 'Staff', 'enabled': True, 'verifier': None}]}


class Rules(unittest.TestCase):
    def setUp(self):
        self.rooms = rules.wanted_rooms([SITE], NAMES)

    def test_addresses_are_fixed_and_safe(self):
        self.assertEqual(rules.site_alias('North Yard / Phase 2'), 'site-north-yard-phase-2')
        self.assertEqual(rules.team_alias('North Yard / Phase 2', 'asha.k'), 'team-north-yard-phase-2-asha.k')
        self.assertEqual(rules.notices_alias('asha.k'), 'notices-asha.k')
        self.assertLessEqual(len(rules.slug('x' * 90)), 40)
        with self.assertRaises(rules.RuleError):
            rules.slug(' // ')

    def test_site_room_holds_everyone_assigned_and_enabled_with_a_chat_name(self):
        site = self.rooms['site-north-yard-phase-2']
        self.assertEqual(site['members'], ['asha.k', 'lata.p', 'meena.s', 'ravi.m'])
        self.assertEqual((site['kind'], site['name'], site['topic']), ('site', 'North Yard', rules.COMPANY_TOPIC))
        self.assertEqual(rules.missing_people([SITE], NAMES), ['nameless@example.net'],
                         'someone without a chat name is reported, not guessed')

    def test_team_room_is_the_supervisor_their_engineer_and_the_project_managers(self):
        team = self.rooms['team-north-yard-phase-2-asha.k']
        self.assertEqual(team['members'], ['asha.k', 'meena.s', 'ravi.m'])
        self.assertEqual(team['name'], 'North Yard: team of Asha K')
        self.assertEqual(self.rooms['team-north-yard-phase-2-lata.p']['members'], ['lata.p', 'meena.s'],
                         'another team: no engineer assigned, and not the first team\'s engineer')

    def test_notices_room_is_one_person_and_read_only(self):
        notices = self.rooms['notices-asha.k']
        self.assertEqual(notices['members'], ['asha.k'])
        self.assertGreater(notices['levels']['events_default'], notices['levels']['users_default'],
                           'a member cannot write there')
        self.assertEqual(self.rooms['site-north-yard-phase-2']['levels']['events_default'], 0, 'members write in a site room')
        for room in self.rooms.values():
            self.assertNotIn('users', room['levels'], 'the creator is not listed: the room rules give it every right')
            self.assertEqual((room['levels']['invite'], room['levels']['kick'], room['levels']['state_default']),
                             (100, 100, 100), 'only the bot invites, removes and changes the room')
        self.assertNotIn('notices-None', self.rooms)

    def test_a_disabled_site_keeps_its_rooms_and_loses_its_people(self):
        rooms = rules.wanted_rooms([dict(SITE, enabled=False)], NAMES)
        self.assertEqual(rooms['site-north-yard-phase-2']['members'], [])
        self.assertEqual(rooms['team-north-yard-phase-2-asha.k']['members'], [])
        self.assertEqual(rooms['notices-asha.k']['members'], ['asha.k'], 'the person keeps their notices')
        self.assertEqual(rules.missing_people([dict(SITE, enabled=False)], NAMES), [])

    def test_membership_changes_never_touch_the_bot_or_another_server(self):
        bot = '@erp:' + SERVER
        present = [bot, '@asha.k:' + SERVER, '@gone.x:' + SERVER, '@guest.y:elsewhere.example']
        invite, remove = rules.membership_changes(['asha.k', 'ravi.m'], present, bot)
        self.assertEqual(invite, ['@ravi.m:' + SERVER])
        self.assertEqual(remove, ['@gone.x:' + SERVER])
        with self.assertRaises(rules.RuleError):
            rules.membership_changes(['Not A Name'], present, bot)

    def test_chat_names(self):
        for good in ('asha.d', 'asha.d2', 'mira.b', 'a.b'):
            self.assertTrue(rules.valid_chat_name(good), good)
        for bad in ('asha', 'Asha.D', 'asha.d@x', 'asha.', '.d', 'as ha.d', '', None, 'asha.dddd'):
            self.assertFalse(rules.valid_chat_name(bad), bad)


class Wire:
    """Records what the bot sends and answers from a list."""
    def __init__(self, answers):
        self.answers, self.sent = list(answers), []

    def __call__(self, method, url, headers, body, timeout):
        self.sent.append((method, url, headers, json.loads(body) if body else None))
        status, content = self.answers.pop(0)
        return status, json.dumps(content).encode()


class Client(unittest.TestCase):
    def bot(self, *answers):
        self.wire = Wire(answers)
        return Bot('http://chat-synapse:8008/', SERVER, 'placeholder-token', send=self.wire)

    def test_every_call_carries_the_token_and_only_there(self):
        bot = self.bot((200, {'room_id': '!r:' + SERVER}))
        self.assertEqual(bot.room_id('site-north-yard'), '!r:' + SERVER)
        method, url, headers, body = self.wire.sent[0]
        self.assertEqual(headers['Authorization'], 'Bearer placeholder-token')
        self.assertEqual(url, 'http://chat-synapse:8008/_matrix/client/v3/directory/room/%23site-north-yard%3Achat.example.net')
        self.assertNotIn('placeholder-token', url)

    def test_a_missing_room_is_none_and_an_error_names_no_credential(self):
        bot = self.bot((404, {'errcode': 'M_NOT_FOUND'}), (403, {'errcode': 'M_FORBIDDEN', 'error': 'placeholder-token'}))
        self.assertIsNone(bot.room_id('site-none'))
        with self.assertRaises(ChatError) as refused:
            bot.invite('!r:' + SERVER, '@asha.k:' + SERVER)
        self.assertEqual((refused.exception.status, refused.exception.code), (403, 'M_FORBIDDEN'))
        self.assertNotIn('placeholder-token', str(refused.exception))

    def test_create_members_and_post(self):
        bot = self.bot((200, {'room_id': '!new:' + SERVER}),
                       (200, {'chunk': [{'state_key': '@a.b:' + SERVER, 'content': {'membership': 'join'}},
                                        {'state_key': '@c.d:' + SERVER, 'content': {'membership': 'invite'}},
                                        {'state_key': '@e.f:' + SERVER, 'content': {'membership': 'leave'}}]}),
                       (200, {}))
        self.assertEqual(bot.create_room('site-x', 'X', 'topic', rules.MEMBER_LEVELS, ['@a.b:' + SERVER]), '!new:' + SERVER)
        created = self.wire.sent[0][3]
        self.assertEqual((created['room_alias_name'], created['preset'], created['invite']), ('site-x', 'private_chat', ['@a.b:' + SERVER]))
        self.assertNotIn('users', created['power_level_content_override'])
        self.assertEqual(bot.members('!new:' + SERVER), ['@a.b:' + SERVER, '@c.d:' + SERVER], 'joined and invited, not left')
        bot.post('!new:' + SERVER, 'approval/42 done', 'Decided.', notice=True)
        method, url, _, body = self.wire.sent[2]
        self.assertEqual((method, body['msgtype']), ('PUT', 'm.notice'))
        self.assertTrue(url.endswith('/send/m.room.message/approval%2F42%20done'), 'the key makes a repeat harmless')

    def test_whether_a_person_has_an_account_and_who_is_only_invited(self):
        bot = self.bot((404, {'errcode': 'M_NOT_FOUND'}), (200, {'displayname': 'Asha K'}),
                       (200, {'chunk': [{'state_key': '@a.b:' + SERVER, 'content': {'membership': 'join'}},
                                        {'state_key': '@c.d:' + SERVER, 'content': {'membership': 'invite'}}]}))
        self.assertFalse(bot.exists('@new.x:' + SERVER), 'no account before the first sign-in')
        self.assertTrue(bot.exists('@asha.k:' + SERVER))
        self.assertTrue(self.wire.sent[0][1].endswith('/_matrix/client/v3/profile/%40new.x%3Achat.example.net'))
        self.assertEqual(bot.states('!r:' + SERVER), {'@a.b:' + SERVER: 'join', '@c.d:' + SERVER: 'invite'})

    def test_no_connection_without_all_three_settings(self):
        for url, server, token in (('', SERVER, 't'), ('http://x', '', 't'), ('http://x', SERVER, '')):
            with self.assertRaises(ChatError):
                Bot(url, server, token)


class MemoryChat:
    """A chat server kept in memory, with the same calls as the bot's client."""
    def __init__(self):
        self.server, self.user_id = SERVER, '@erp:' + SERVER
        self.rooms, self.fail = {}, set()
        self.no_account, self.pending = set(), set()

    def exists(self, user):
        return user.split(':')[0][1:] not in self.no_account

    def states(self, room_id):
        return {m: ('invite' if (room_id[1:], m) in self.pending else 'join')
                for m in self.rooms[room_id[1:]]['members']}

    def room_id(self, alias):
        if alias in self.fail:
            raise ChatError('The chat server answered 500 (no code).', 500)
        return '!' + alias if alias in self.rooms else None

    def create_room(self, alias, name, topic, levels, invite=()):
        self.rooms[alias] = {'name': name, 'topic': topic, 'levels': dict(levels), 'members': {self.user_id, *invite}}
        return '!' + alias

    def members(self, room_id):
        return sorted(self.rooms[room_id[1:]]['members'])

    def invite(self, room_id, user):
        self.rooms[room_id[1:]]['members'].add(user)
        self.pending.discard((room_id[1:], user))  # an invitation to an existing account is accepted at once

    def remove(self, room_id, user, reason):
        self.rooms[room_id[1:]]['members'].discard(user)
        self.pending.discard((room_id[1:], user))

    def name(self, room_id):
        return self.rooms[room_id[1:]]['name']

    def rename(self, room_id, name):
        self.rooms[room_id[1:]]['name'] = name


class Applying(unittest.TestCase):
    def setUp(self):
        self.logged = []
        self.saved = getattr(FRAPPE, 'log_error', None)
        FRAPPE.log_error = lambda title=None, message=None: self.logged.append((title, message))
        self.chat = MemoryChat()

    def tearDown(self):
        if self.saved is None:
            del FRAPPE.log_error
        else:
            FRAPPE.log_error = self.saved

    def people(self, alias):
        return sorted(m.split(':')[0][1:] for m in self.chat.rooms[alias]['members'] if m != self.chat.user_id)

    def test_first_run_creates_and_a_second_run_changes_nothing(self):
        wanted = rules.wanted_rooms([SITE], NAMES)
        first = sync.apply(self.chat, wanted)
        self.assertEqual((first['created'], first['failed']), (len(wanted), 0))
        self.assertEqual(self.people('site-north-yard-phase-2'), ['asha.k', 'lata.p', 'meena.s', 'ravi.m'])
        self.assertEqual(sync.apply(self.chat, wanted), {'created': 0, 'invited': 0, 'removed': 0, 'renamed': 0,
                                                         'failed': 0, 'not_signed_in_yet': 0})

    def test_someone_who_never_signed_in_to_chat_waits_and_is_added_after_their_first_sign_in(self):
        self.chat.no_account = {'ravi.m'}
        wanted = rules.wanted_rooms([SITE], NAMES)
        first = sync.apply(self.chat, wanted)
        self.assertEqual(first['not_signed_in_yet'], 1)
        self.assertEqual(self.people('site-north-yard-phase-2'), ['asha.k', 'lata.p', 'meena.s'], 'no early invitation')
        self.assertNotIn('notices-ravi.m', self.chat.rooms)
        self.chat.no_account = set()
        later = sync.apply(self.chat, wanted)
        self.assertEqual(self.people('site-north-yard-phase-2'), ['asha.k', 'lata.p', 'meena.s', 'ravi.m'])
        self.assertEqual(self.people('team-north-yard-phase-2-asha.k'), ['asha.k', 'meena.s', 'ravi.m'])
        self.assertIn('notices-ravi.m', self.chat.rooms)
        self.assertEqual(later['not_signed_in_yet'], 0)

    def test_a_pending_invitation_is_made_again_or_withdrawn(self):
        wanted = rules.wanted_rooms([SITE], NAMES)
        sync.apply(self.chat, wanted)
        room, person = 'site-north-yard-phase-2', '@ravi.m:' + SERVER
        self.chat.pending.add((room, person))
        result = sync.apply(self.chat, wanted)
        self.assertEqual(self.chat.states('!' + room)[person], 'join', 'the invitation was made again and accepted')
        self.assertEqual(result['invited'], 1)
        self.chat.pending.add((room, person))
        self.chat.no_account = {'ravi.m'}
        sync.apply(self.chat, wanted)
        self.assertNotIn(person, self.chat.rooms[room]['members'], 'an invitation to a missing account is withdrawn')

    def test_a_change_of_assignment_invites_and_removes_and_a_new_name_renames(self):
        sync.apply(self.chat, rules.wanted_rooms([SITE], NAMES))
        changed = dict(SITE, label='North Yard (Phase 2)', members=[
            m if m['user'] != 'eng@example.net' else dict(m, enabled=False) for m in SITE['members']
        ] + [{'user': 'staff@example.net', 'team_role': 'Staff', 'enabled': True, 'verifier': None}])
        result = sync.apply(self.chat, rules.wanted_rooms([changed], NAMES))
        self.assertEqual(self.people('site-north-yard-phase-2'), ['asha.k', 'john.d', 'lata.p', 'meena.s'])
        self.assertEqual(self.people('team-north-yard-phase-2-asha.k'), ['asha.k', 'meena.s'], 'the engineer left the team too')
        self.assertEqual(self.chat.rooms['site-north-yard-phase-2']['name'], 'North Yard (Phase 2)')
        self.assertGreaterEqual(result['removed'], 2)
        self.assertGreaterEqual(result['renamed'], 1)

    def test_an_empty_room_is_not_created_and_a_disabled_site_empties_its_rooms(self):
        nobody = dict(SITE, name='Empty', label='Empty', members=[])
        sync.apply(self.chat, rules.wanted_rooms([nobody], {}))
        self.assertEqual(self.chat.rooms, {})
        sync.apply(self.chat, rules.wanted_rooms([SITE], NAMES))
        sync.apply(self.chat, rules.wanted_rooms([dict(SITE, enabled=False)], NAMES))
        self.assertEqual(self.people('site-north-yard-phase-2'), [])
        self.assertEqual(self.people('notices-asha.k'), ['asha.k'])

    def test_one_failing_room_is_logged_without_stopping_the_rest(self):
        self.chat.fail.add('site-north-yard-phase-2')
        result = sync.apply(self.chat, rules.wanted_rooms([SITE], NAMES))
        self.assertEqual(result['failed'], 1)
        self.assertIn('team-north-yard-phase-2-asha.k', self.chat.rooms)
        self.assertEqual(self.logged[0][0], 'Chat room not updated')
        self.assertIn('site-north-yard-phase-2', self.logged[0][1])

    def test_nothing_runs_without_the_private_setting(self):
        saved = dict(FRAPPE.conf)
        try:
            FRAPPE.conf.clear()
            self.assertIsNone(sync.settings())
            self.assertIsNone(sync.sync_all())
            FRAPPE.conf['chat_rooms'] = {'url': 'http://chat-synapse:8008', 'server_name': SERVER}
            self.assertIsNone(sync.settings(), 'all three are needed')
        finally:
            FRAPPE.conf.clear()
            FRAPPE.conf.update(saved)


class Wiring(unittest.TestCase):
    def test_the_feature_is_loaded_and_its_hooks_name_real_functions(self):
        hooks = (ROOT / 'erpnext_drive_integrations/hooks.py').read_text(encoding='utf-8')
        self.assertIn('"chat_rooms"', hooks)
        fragment = (ROOT / 'erpnext_drive_integrations/chat_rooms/hooks.py').read_text(encoding='utf-8')
        for name in ('install', 'site_changed', 'validate_user', 'user_changed', 'sync_all'):
            self.assertIn('chat_rooms.sync.' + name, fragment)
            self.assertTrue(callable(getattr(sync, name)), name)

    def test_the_chat_server_lets_the_bot_own_these_addresses(self):
        configure = (ROOT / 'integrations/chat/configure.py').read_text(encoding='utf-8')
        self.assertIn("'#(site|team|notices)-.*:'", configure)
        for alias in (rules.site_alias('x'), rules.team_alias('x', 'a.b'), rules.notices_alias('a.b')):
            self.assertRegex(alias, r'^(site|team|notices)-')


if __name__ == '__main__':
    unittest.main()
