frappe.pages['field-attendance'].on_page_load = function(wrapper) {
  const page = frappe.ui.make_app_page({parent: wrapper, title: __('Field Attendance'), single_column: true});
  const frame = document.createElement('iframe');
  frame.src = '/field-team?embedded=1';
  frame.title = __('Field Attendance');
  frame.allow = 'camera; geolocation';
  frame.style.cssText = 'width:100%;height:calc(100dvh - 135px);min-height:560px;border:0;display:block;';
  page.main.css({padding: 0, maxWidth: 'none', width: '100%'}).empty().append(frame);
};
