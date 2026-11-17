# Local v0.5 implementation contract
All JSON API; errors {error}. POST same-origin, session cookie HttpOnly SameSite=Strict; auth POST login and password APIs below. All private endpoints require session. Public /api/catalog retains original array, /api/state?operator,after sanitized queue payload, /api/settings branding settings only, /api/ticket original contract.

Auth: GET /api/me -> {user:null|{id,username,full_name,role,department,operator,must_change_password}}. POST /api/login {username,password} -> {user}; POST /api/logout {}; POST /api/password {current_password,new_password}. Demo users admin, manager, manager2, executor, head, director; password Navbot-Test-2026! (demo only --seed-demo). role values admin/manager/executor/head/director. First login demo users NOT forced password change (explicit demo); created/reset accounts must change.
GET /api/users -> {users:[{id,username,full_name,role,department,operator}]} (routing directory).
POST /api/student {hemis_id} -> {student:null|{hemis_id,full_name,faculty,programme,course,student_group,education_form,status},source:'local'}. Accept numeric or H-prefixed uppercase ID 6-20 ASCII chars. GET /api/students -> {students:[...]}, role admin/head/director. POST /api/students/import {students:[same fields]} admin only; transactional upsert; returns {added,updated}.
POST /api/action {operator,action:'call'|'recall'|'start'|'finish'} retains queue semantics but manager/admin only; manager limited to own operator. finish only ends physical queue; request remains separately tracked.

GET /api/requests -> {requests:[request...]}; server role scoped: manager own, executor assigned, head department + pending approvals in department, director/admin all. Each request includes id,number:'NAV-0001',ticket_id,queue_number|null,lang,section,service,student_id,student:object|null,content,note,channel:kiosk|phone,manager_id,assignee_id,department,status:new|in_progress|returned|pending_approval|closed,deadline:ISO UTC|null,internal_basis,legal_basis,answer,result,unresolved_reason,created_at,updated_at,answered_at,closed_at,version,history:[{id,actor,action,detail,created_at}],manager_name,assignee_name. Backend autogenerates one request per kiosk ticket. Queue and request states independent.
POST /api/request/create {key:UUID,channel:'phone',section,service,lang,hemis_id,identity_confirmed:true,content,note} manager/admin; no queue number for phone.
POST /api/request/action {id,version,action,...} -> {request} (optimistic version, 409 stale). Actions:
- update {hemis_id,content,note} manager owner/admin, before pending/closed
- assign {assignee_id,deadline,internal_basis,legal_basis,reason} manager owner/admin; student required, deadline future ISO w/timezone on initial assign. reassign after return must retain existing deadline/bases; reason required. can assign self to retain.
- return {reason} current executor only; manager notified, status returned, same number/deadline
- submit {answer} current assignee -> pending_approval; head notified
- approve {result} head of department or admin -> closed, needs answer
- correct {reason} head of department/admin -> in_progress, assignee notified
- resolve {answer,result} manager owner/admin with student -> close locally
- deadline {deadline,reason,internal_basis,legal_basis} head/admin only, history old/new values preserved
GET /api/notifications -> {notifications:[{id,request_id,message,read,created_at}]}; POST /api/notification/read {id} marks own.
GET /api/report?from=YYYY-MM-DD&to=YYYY-MM-DD&department=&channel=&status=&manager_id=&section=&service= -> {summary:{total,in_progress,overdue,closed,on_time},departments:[{department,total,closed,overdue}],daily:[{date,total}],requests:[...]} role head/director/admin with department scoping; CSV GET /api/report.csv same params.
GET /api/audit -> {events:[{id,actor,action,detail,created_at}]} admin only.
POST /api/admin/user {username,full_name,role,department,operator,password} -> {user}; POST /api/admin/reset {user_id,password}; POST /api/admin/settings {settings} -> {settings}; admin only.
Settings GET {settings:{university:[uz,ru,en],office:[uz,ru,en],tv_language:'uz',warning_hours:24,volume:0.75,blink_count:3,tv_titles:[[uz..],[ru..],[en..]],operator_labels:{'1':['1-operator','1-е окно','counter 1']},voice_templates:[...],catalog:original catalog, hidden_services:['0:1'],receipt_footer:[uz,ru,en]}}. Admin sets supported fields. Existing request content/bases remain snapshots. Logo upload/templates/real integration adapters may follow after core acceptance, never show false connected.
GET /api/integrations -> {lms:{connected:false},telegram:{connected:false}}. No fake external identity/notifications. In-app polling notifications only, clearly local.
UI routes /kiosk /tv /tablo public; /login /operator /manager /executor /head /director /admin /profile app shell. Links to public views. Admin settings UI, users/import, audit; reporting filters + download. User UI uses Uzbek new script as practical, localization kiosk/receipt/voice mandatory. Demo login card explicitly local test credentials.

Logo: settings.section_logos = [null|string data PNG/JPEG URL] x5. POST /api/admin/logo {section:0..4,mime:"image/png"|"image/jpeg",data:base64}, max2MiB -> {settings}. Logo values in settings save must remain unchanged (use upload endpoint).
Request update/resolve of another assignee's in-progress request rejected; return it first. Existing deadline always retained during assign/reassign. Queue state mutations advance request version for history. Ticket content is an immutable stored service-name snapshot.
