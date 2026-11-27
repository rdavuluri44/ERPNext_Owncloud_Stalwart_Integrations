"""Keep the chat rooms in step with the sites (P73): the Frappe side of `rules.py` and `matrix.py`.

Runs after a Field Site or a person's chat name changes (in the background, after the change is saved) and once
an hour for everything, so a missed run heals itself. It does nothing on a site without the private setting
`chat_rooms` = {"url": the chat server inside the private network, "server_name": its name, "token": the bot's
token}. A problem with the chat server never stops a save in the business system; it is logged without any
credential and tried again at the next run.
"""
import frappe

from erpnext_drive_integrations.chat_rooms import rules
from erpnext_drive_integrations.chat_rooms.matrix import Bot, ChatError

CHAT_NAME_FIELD = 'custom_chat_name'
REMOVED_REASON = 'No longer assigned'


def settings():
    conf = frappe.conf.get('chat_rooms') or {}
    return conf if conf.get('url') and conf.get('server_name') and conf.get('token') else None


def bot():
    conf = settings()
    return Bot(conf['url'], conf['server_name'], conf['token']) if conf else None


def install():
    """The person's chat name on their User record: set by an administrator until the sign-up service does it
    (P82). It is made once (`firstname.initial`) and not changed afterwards."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({'User': [dict(
        fieldname=CHAT_NAME_FIELD, label='Chat name', fieldtype='Data', insert_after='username', unique=1,
        no_copy=1, description='firstname.initial, as held by the sign-in service. Never changed once used.')]},
        update=True)


def validate_user(doc, method=None):
    name = (doc.get(CHAT_NAME_FIELD) or '').strip() or None
    doc.set(CHAT_NAME_FIELD, name)
    if name and not rules.valid_chat_name(name):
        frappe.throw('A chat name is firstname.initial, with an optional number: asha.d, asha.d2')
    before = doc.get_doc_before_save() if hasattr(doc, 'get_doc_before_save') else None
    if before and before.get(CHAT_NAME_FIELD) and before.get(CHAT_NAME_FIELD) != name:
        frappe.throw('A chat name is not changed once it is set: the chat address cannot be renamed.')


def collect():
    """Every site with its member rows, and every enabled person's chat name."""
    people = frappe.get_all('User', filters={'enabled': 1, CHAT_NAME_FIELD: ['is', 'set']},
                            fields=['name', 'full_name', CHAT_NAME_FIELD])
    chat_names = {p['name']: p[CHAT_NAME_FIELD] for p in people}
    labels = {p['name']: p['full_name'] for p in people}
    sites = []
    for site in frappe.get_all('Field Site', fields=['name', 'site_name', 'enabled']):
        rows = frappe.get_all('Field Site Member', filters={'parent': site['name'], 'parenttype': 'Field Site'},
                              fields=['user', 'team_role', 'enabled', 'verifier'])
        sites.append({'name': site['name'], 'label': site['site_name'], 'enabled': bool(site['enabled']),
                      'members': [dict(row, enabled=bool(row['enabled'])) for row in rows], 'labels': labels})
    return sites, chat_names


def apply(chat, wanted):
    """Make each wanted room real. Returns counts; one room's failure does not stop the others."""
    done = {'created': 0, 'invited': 0, 'removed': 0, 'renamed': 0, 'failed': 0, 'not_signed_in_yet': 0}
    known, waiting = {}, set()

    def has_account(name):
        """A chat account is made at a person's first sign-in. Until then they are not invited: an invitation
        is accepted automatically only at the moment it is made, so an early one would stay pending."""
        if name not in known:
            known[name] = chat.exists(rules.user_id(name, chat.server))
        if not known[name]:
            waiting.add(name)
        return known[name]

    for alias, room in sorted(wanted.items()):
        try:
            members = [name for name in room['members'] if has_account(name)]
            room_id = chat.room_id(alias)
            if not room_id:
                if members:
                    chat.create_room(alias, room['name'], room['topic'], room['levels'],
                                     [rules.user_id(name, chat.server) for name in members])
                    done['created'] += 1
                    done['invited'] += len(members)
                continue
            states = chat.states(room_id)
            invite, remove = rules.membership_changes(members, sorted(states), chat.user_id)
            # Someone still only invited although their account exists: make the invitation again, so it is accepted.
            again = [person for person, state in sorted(states.items()) if state == 'invite' and person not in remove]
            for person in remove + again:
                chat.remove(room_id, person, REMOVED_REASON)
            for person in invite + again:
                chat.invite(room_id, person)
            done['invited'] += len(invite) + len(again)
            done['removed'] += len(remove)
            if chat.name(room_id) != room['name']:
                chat.rename(room_id, room['name'])
                done['renamed'] += 1
        except (ChatError, rules.RuleError) as error:
            done['failed'] += 1
            frappe.log_error(title='Chat room not updated', message='%s: %s' % (alias, error))
    done['not_signed_in_yet'] = len(waiting)
    return done


def sync_all():
    chat = bot()
    if not chat:
        return None
    sites, chat_names = collect()
    result = apply(chat, rules.wanted_rooms(sites, chat_names))
    result['without_chat_name'] = len(rules.missing_people(sites, chat_names))
    return result


def sync_site(site):
    """Only the rooms of one site (and its members' Notices rooms), right after it changed."""
    chat = bot()
    if not chat:
        return None
    sites, chat_names = collect()
    mine = [s for s in sites if s['name'] == site]
    if not mine:
        return None
    members = {m['user'] for m in mine[0]['members']}
    return apply(chat, rules.wanted_rooms(mine, {u: n for u, n in chat_names.items() if u in members}))


def site_changed(doc, method=None):
    if settings():
        frappe.enqueue('erpnext_drive_integrations.chat_rooms.sync.sync_site', queue='short', site=doc.name,
                       enqueue_after_commit=True)


def user_changed(doc, method=None):
    if settings() and (doc.has_value_changed(CHAT_NAME_FIELD) or doc.has_value_changed('enabled')):
        frappe.enqueue('erpnext_drive_integrations.chat_rooms.sync.sync_all', queue='short',
                       enqueue_after_commit=True)


def notify(user, key, text):
    """One informing message into a person's Notices room (for the notification service, P108). Returns False
    when the person has no chat name, has never signed in to chat, or chat is not set up; a repeat with the same
    key posts nothing new."""
    chat = bot()
    chat_name = frappe.db.get_value('User', {'name': user, 'enabled': 1}, CHAT_NAME_FIELD)
    if not chat or not rules.valid_chat_name(chat_name):
        return False
    alias = rules.notices_alias(chat_name)
    person = rules.user_id(chat_name, chat.server)
    if not chat.exists(person):
        return False
    room_id = chat.room_id(alias) or chat.create_room(alias, 'Notices', rules.NOTICES_TOPIC, rules.READ_ONLY_LEVELS,
                                                      [person])
    chat.post(room_id, key, text, notice=True)
    return True
