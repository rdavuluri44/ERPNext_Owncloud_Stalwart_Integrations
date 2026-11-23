"""Approved SSO user provisioning and portal installation defaults."""
import frappe

def enabled():
 return bool(frappe.conf.get('cloud_combined_site'))

def new_central_user(doc, method=None):
 if enabled() and doc.flags.get('cloud_central_provision'):
  doc.set('roles', [r for r in doc.roles if r.role == 'Desk User'])

def ensure_user(email,info,claims):
 from .sso import is_approved
 if (not is_approved(claims) or info.get('email_verified') is not True
     or info.get('sub')!=claims.get('sub') or str(info.get('email','')).lower()!=email):
  raise frappe.AuthenticationError('This identity is not approved')
 if not frappe.db.exists('User',email):
  user=frappe.get_doc({'doctype':'User','email':email,'enabled':1,'send_welcome_email':0,
   'first_name':info.get('given_name') or info.get('name') or email.split('@')[0],
   'roles':[{'role':'Desk User'}]})
  user.flags.cloud_central_provision=True
  user.insert(ignore_permissions=True)
  # Signup hooks must not assign business access. Administrator assigns it later.
  frappe.db.delete('Has Role',{'parent':email,'parenttype':'User','role':['!=','Desk User']})
  frappe.clear_cache(user=email)
 if not frappe.db.get_value('User',email,'enabled'):
  raise frappe.AuthenticationError('This account is disabled')

def configure():
 if not enabled():return
 frappe.db.set_single_value('Website Settings','home_page','place_holder')
 frappe.db.set_single_value('Website Settings','disable_signup',1)
 frappe.db.commit()

def prepare():
 if enabled() and not frappe.db.exists('Role','Mailbox Administrator'):
  frappe.get_doc({'doctype':'Role','role_name':'Mailbox Administrator','desk_access':1}).insert(ignore_permissions=True)
