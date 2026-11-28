"""Which chat rooms should exist and who belongs in them (P73). Pure rules: no Frappe, no network.

The business system's bot keeps three kinds of room in step with the sites (owner, 27 November 2026):

* a **site room** per enabled site, for everyone assigned to that site;
* a **team room** per supervisor at a site, for that supervisor, the engineer assigned to them and the site's
  project managers (approvers);
* a read-only **Notices room** per person, for system messages that only inform.

Nothing about rooms is stored in the business system. A room is found by its fixed address (alias), made from the
site's record name and, for a team, the supervisor's chat name, and the members are read from the chat server every
time. A person takes part only when they have a chat name (`firstname.initial`, held by the sign-in service).
"""
import re

CHAT_NAME = re.compile(r'[a-z][a-z0-9]*\.[a-z][a-z0-9]{0,2}')
COMPANY_TOPIC = 'Company room. Messages here are kept by the company.'
NOTICES_TOPIC = 'Messages from the system that only inform. Nobody can reply here.'
# Members may write; only the room's creator (the bot) may invite, remove, rename or change the rules. In a
# Notices room writing needs more than a member has. The creator is not listed: the room rules give it every right.
MEMBER_LEVELS = {'users_default': 0, 'events_default': 0, 'state_default': 100, 'invite': 100, 'kick': 100,
                 'ban': 100, 'redact': 100}
READ_ONLY_LEVELS = dict(MEMBER_LEVELS, events_default=50)


class RuleError(ValueError):
    pass


def slug(text, limit=40):
    """A fixed, address-safe form of a record name: lower-case letters, digits and single hyphens."""
    value = re.sub(r'[^a-z0-9]+', '-', str(text or '').lower()).strip('-')[:limit].strip('-')
    if not value:
        raise RuleError('A room needs a name with at least one letter or digit.')
    return value


def valid_chat_name(name):
    return bool(name) and bool(CHAT_NAME.fullmatch(str(name)))


def user_id(chat_name, server):
    if not valid_chat_name(chat_name):
        raise RuleError('Not a chat name: firstname.initial, with an optional number.')
    return '@%s:%s' % (chat_name, server)


def site_alias(site):
    return 'site-' + slug(site)


def team_alias(site, supervisor_chat_name):
    return 'team-%s-%s' % (slug(site, 30), supervisor_chat_name)


def notices_alias(chat_name):
    return 'notices-' + chat_name


def wanted_rooms(sites, chat_names):
    """The rooms that should exist, as {alias: {'kind', 'name', 'topic', 'levels', 'members'}}.

    `sites` is a list of {'name', 'label', 'enabled', 'labels': {user: full name, for team room titles},
    'members': [{'user', 'team_role', 'enabled', 'verifier'}]}; `chat_names` maps a user to their chat name.
    People without a valid chat name are left out and reported by `missing_people`. A disabled site keeps its
    rooms but with no members, so its people are removed.
    """
    rooms = {}
    for site in sites:
        active = [m for m in site.get('members') or [] if m.get('enabled') and site.get('enabled')]
        named = lambda user: chat_names.get(user) if valid_chat_name(chat_names.get(user)) else None  # noqa: E731
        everyone = sorted({named(m['user']) for m in active} - {None})
        rooms[site_alias(site['name'])] = {
            'kind': 'site', 'name': site.get('label') or site['name'], 'topic': COMPANY_TOPIC,
            'levels': MEMBER_LEVELS, 'members': everyone}
        approvers = {named(m['user']) for m in active if m.get('team_role') == 'Approver'} - {None}
        engineers = {m['user'] for m in active if m.get('team_role') == 'Verifier'}
        for row in site.get('members') or []:
            if row.get('team_role') != 'Supervisor' or not named(row['user']):
                continue
            running = row.get('enabled') and site.get('enabled')
            # The engineer named on the supervisor's row counts only while they are an active engineer of the site.
            engineer = named(row.get('verifier')) if row.get('verifier') in engineers else None
            team = {named(row['user']), engineer} | approvers if running else set()
            label = (site.get('labels') or {}).get(row['user']) or chat_names[row['user']]
            rooms[team_alias(site['name'], named(row['user']))] = {
                'kind': 'team', 'name': '%s: team of %s' % (site.get('label') or site['name'], label),
                'topic': COMPANY_TOPIC, 'levels': MEMBER_LEVELS, 'members': sorted(team - {None})}
    for user, chat_name in sorted(chat_names.items()):
        if valid_chat_name(chat_name):
            rooms[notices_alias(chat_name)] = {'kind': 'notices', 'name': 'Notices', 'topic': NOTICES_TOPIC,
                                               'levels': READ_ONLY_LEVELS, 'members': [chat_name]}
    return rooms


def missing_people(sites, chat_names):
    """Enabled site members who cannot be put into any room because they have no valid chat name."""
    return sorted({m['user'] for site in sites if site.get('enabled') for m in site.get('members') or []
                   if m.get('enabled') and not valid_chat_name(chat_names.get(m['user']))})


def membership_changes(wanted, present, bot):
    """Who to invite and who to remove, given the chat names wanted and the user IDs now joined or invited.

    The bot itself is never removed, and neither is anyone from another server (there is none without
    federation; if one ever appears, a person must look at it)."""
    server = bot.split(':', 1)[1]
    wanted_ids = {user_id(name, server) for name in wanted}
    here = {member for member in present if member != bot}
    return sorted(wanted_ids - here), sorted(m for m in here - wanted_ids if m.endswith(':' + server))
