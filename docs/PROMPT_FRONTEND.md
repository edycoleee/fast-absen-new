# Prompt AI - Frontend (React + Vite + Tailwind) — Sistem Absensi RSUD Sulfat

Gunakan prompt ini untuk membuat ulang frontend sistem absensi RSUD Sulfat yang sudah dalam kondisi final.

---

## 🤖 PROMPT UNTUK AI

```
Buatkan saya aplikasi frontend React (Vite) production-ready sebagai admin dashboard
untuk sistem absensi rumah sakit (RSUD Sulfat).

## Requirements:

### 1. Tech Stack
- React 18.3+
- Vite 6+ (dev: --host 0.0.0.0)
- Tailwind CSS 3.4+
- Axios 1.6+
- React Router DOM 6.22+
- PostCSS + Autoprefixer

### 2. Struktur Project
```
frontend/
├── public/
├── src/
│   ├── core/
│   │   ├── constants/
│   │   │   ├── config.js       # API_CONFIG, STORAGE_KEYS, PAGINATION, DATE_FORMAT, ABSENSI_STATUS, PEGAWAI_STATUS, APP_META
│   │   │   ├── routes.js       # ROUTES object
│   │   │   └── index.js
│   │   ├── entities/
│   │   │   ├── User.js         # User factory: { id, username, roles[], permissions[], menu_guard{} }
│   │   │   ├── Pegawai.js
│   │   │   ├── Role.js
│   │   │   ├── Permission.js
│   │   │   ├── Absensi.js
│   │   │   └── index.js
│   │   └── index.js
│   ├── data/
│   │   ├── api/
│   │   │   └── client.js       # Axios instance + request/response interceptors
│   │   ├── repositories/
│   │   │   ├── AuthRepository.js
│   │   │   ├── UserRepository.js
│   │   │   ├── RoleRepository.js
│   │   │   ├── PermissionRepository.js
│   │   │   ├── PegawaiRepository.js
│   │   │   ├── UnitRepository.js
│   │   │   ├── ShiftKelompokRepository.js
│   │   │   ├── AppConfigRepository.js            # GET + PUT /app-config/ (singleton)
│   │   │   ├── PegawaiShiftKelompokRepository.js # tipe_shift: SHIFT|NON_SHIFT
│   │   │   ├── RosterUploadBatchRepository.js
│   │   │   ├── RosterShiftRepository.js
│   │   │   ├── PenilaianShiftAbsensiRepository.js
│   │   │   ├── ApprovalRepository.js
│   │   │   ├── AbsensiRepository.js
│   │   │   ├── SessionsRepository.js
│   │   │   ├── StatsRepository.js
│   │   │   └── index.js
│   │   ├── storage/
│   │   │   └── LocalStorage.js # getItem/setItem/removeItem (auto JSON parse/stringify)
│   │   └── index.js
│   ├── domain/
│   │   ├── contexts/
│   │   │   └── AuthContext.jsx # AuthProvider + useAuth
│   │   ├── hooks/
│   │   │   ├── useAuth.js
│   │   │   ├── useUsers.js
│   │   │   ├── useRoles.js
│   │   │   ├── usePegawai.js
│   │   │   ├── useUnits.js
│   │   │   ├── useShiftKelompok.js
│   │   │   ├── useAppConfig.js           # Global evaluation config
│   │   │   ├── usePegawaiShiftKelompok.js
│   │   │   ├── useRosterUploadBatch.js
│   │   │   ├── useRosterShift.js
│   │   │   ├── usePenilaianShiftAbsensi.js
│   │   │   ├── useAbsensi.js
│   │   │   ├── useSessionHeartbeat.js    # Heartbeat ping backend setiap N menit
│   │   │   └── index.js
│   │   └── index.js
│   ├── presentation/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── PrivateRoute.jsx           # Admin guarded route (redirect ke /login-admin)
│   │   │   │   ├── AttendancePrivateRoute.jsx # Pegawai guarded route (redirect ke /login-absensi)
│   │   │   │   ├── PegawaiSearchInput.jsx
│   │   │   │   └── UnitSearchInput.jsx
│   │   │   └── layout/
│   │   │       └── Layout.jsx  # Responsive sidebar + topbar
│   │   └── pages/
│   │       ├── auth/
│   │       │   ├── AdminLoginPage.jsx          # Login admin (username/password)
│   │       │   ├── AttendanceLoginPage.jsx     # Login pegawai (terminal absensi)
│   │       │   └── index.js
│   │       ├── public/
│   │       │   ├── LandingPage.jsx             # Pilih: masuk admin / terminal absensi
│   │       │   └── index.js
│   │       ├── admin/
│   │       │   ├── AdminDashboardPage.jsx
│   │       │   ├── UsersPage.jsx
│   │       │   ├── RolesPage.jsx
│   │       │   ├── PermissionsPage.jsx
│   │       │   ├── UnitsPage.jsx
│   │       │   ├── EmployeesPage.jsx           # Pegawai CRUD + foto upload
│   │       │   ├── ShiftKelompokPage.jsx        # Master klasifikasi roster
│   │       │   ├── AppConfigPage.jsx            # ⚙️ Config evaluasi global (form GET+PUT)
│   │       │   ├── PegawaiShiftKelompokPage.jsx # tipe_shift per pegawai + import Excel
│   │       │   ├── RosterUploadBatchPage.jsx
│   │       │   ├── RosterAdapterPage.jsx        # Upload + preview sebelum import
│   │       │   ├── RosterShiftPage.jsx
│   │       │   ├── PenilaianShiftAbsensiPage.jsx
│   │       │   ├── AttendanceMonitorPage.jsx    # Admin monitoring absensi
│   │       │   ├── ApprovalPage.jsx
│   │       │   ├── SessionMonitorPage.jsx
│   │       │   ├── KpiUnitRolePage.jsx
│   │       │   └── index.js
│   │       ├── attendance/
│   │       │   ├── AttendanceDashboardPage.jsx  # Pegawai: check-in/check-out + history
│   │       │   └── index.js
│   │       └── index.js
│   ├── utils/
│   │   └── errorHandler.js
│   ├── App.jsx
│   ├── index.css
│   └── main.jsx
├── index.html
├── package.json
├── tailwind.config.js
├── postcss.config.js
├── vite.config.js
└── .env
```

### 3. Routing (App.jsx)

Dua jalur autentikasi terpisah:
- Admin: `/login-admin` → `PrivateRoute` → `Layout` (sidebar)
- Pegawai: `/login-absensi` → `AttendancePrivateRoute` → halaman absensi (tanpa sidebar)

`SessionHeartbeatRunner` adalah komponen kecil di dalam `AuthProvider` yang memanggil `useSessionHeartbeat(5)`.

```jsx
function App() {
  return (
    <AuthProvider>
      <SessionHeartbeatRunner />
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login-admin" element={<AdminLoginPage />} />
          <Route path="/login-absensi" element={<AttendanceLoginPage />} />

          <Route path="/absensi-dashboard" element={<AttendancePrivateRoute />}>
            <Route index element={<AttendanceDashboardPage />} />
          </Route>

          <Route path="/" element={<PrivateRoute />}>
            <Route path="dashboard"         element={<AdminDashboardPage />} />
            <Route path="users"             element={<UsersPage />} />
            <Route path="roles"             element={<RolesPage />} />
            <Route path="permissions"       element={<PermissionsPage />} />
            <Route path="unit"              element={<UnitsPage />} />
            <Route path="pegawai"           element={<EmployeesPage />} />
            <Route path="shift-kelompok"    element={<ShiftKelompokPage />} />
            <Route path="app-config"        element={<AppConfigPage />} />
            <Route path="shift-pegawai"     element={<PegawaiShiftKelompokPage />} />
            <Route path="roster-upload"     element={<RosterUploadBatchPage />} />
            <Route path="roster-adapter"    element={<RosterAdapterPage />} />
            <Route path="roster-shift"      element={<RosterShiftPage />} />
            <Route path="penilaian-shift"   element={<PenilaianShiftAbsensiPage />} />
            <Route path="absensi"           element={<AttendanceMonitorPage />} />
            <Route path="sessions-monitor"  element={<SessionMonitorPage />} />
            <Route path="approval"          element={<ApprovalPage />} />
            <Route path="rekap-unit-role"   element={<KpiUnitRolePage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

### 4. API Client (data/api/client.js)

```js
const apiClient = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,  // ✅ Wajib untuk refresh token via httpOnly cookie
});

// Request: inject Bearer token dari localStorage
apiClient.interceptors.request.use((config) => {
  const token = LocalStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response: auto-refresh token saat 401
apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const { data } = await axios.post(
          `${API_CONFIG.BASE_URL}/auth/refresh`, {}, { withCredentials: true }
        );
        if (data.success) {
          LocalStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.data.access_token);
          if (data.data.user) {
            LocalStorage.setItem(STORAGE_KEYS.USER, data.data.user);
            // 🔥 Beritahu AuthContext agar sync state tanpa logout/login ulang
            window.dispatchEvent(new CustomEvent('auth:user-refreshed', { detail: data.data.user }));
          }
          original.headers.Authorization = `Bearer ${data.data.access_token}`;
          return apiClient(original);
        }
      } catch {
        LocalStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
        LocalStorage.removeItem(STORAGE_KEYS.USER);
        window.location.href = '/login-admin';
      }
    }
    return Promise.reject(error);
  }
);
```

### 5. AuthContext

```jsx
// State: { user, loading, error }
// user: { id, username, roles[], permissions[], menu_guard{} }
// menu_guard didapat dari backend saat login, menentukan menu apa yang visible

// Login: simpan access_token + session_id + user ke localStorage
// Logout: call POST /auth/logout, bersihkan localStorage + state
// isAuthenticated(): cek user + token di localStorage
// hasRole(name): cek roles array
// isAdmin(): hasRole('admin') || hasRole('super-admin')

// Sync state saat token di-refresh oleh interceptor:
useEffect(() => {
  const handler = (event) => setUser(User(event.detail || LocalStorage.getItem(STORAGE_KEYS.USER)));
  window.addEventListener('auth:user-refreshed', handler);
  return () => window.removeEventListener('auth:user-refreshed', handler);
}, []);
```

### 6. RBAC: menu_guard dari Backend

Jangan hardcode permission check di frontend. Backend mengembalikan `menu_guard` saat login.
Sidebar dibangun **dinamis dari `menu_guard`**:

```js
// Layout.jsx
const buildMenuItems = (menuGuard = {}) => {
  const menus = menuGuard?.menus ?? {};
  const isAdmin = !!menuGuard?.is_admin;
  const items = [];

  // Operational — ikuti menus.*.visible dari server
  if (menus.dashboard?.visible)           items.push({ path: '/dashboard',      label: 'Dashboard',         icon: '📊' });
  if (menus.kpi_unit_role?.visible)       items.push({ path: '/rekap-unit-role', label: 'Rekap Unit/Role',  icon: '📈' });
  if (menus.monitoring_absensi?.visible)  items.push({ path: '/absensi',         label: 'Monitoring Absensi', icon: '📝' });
  if (menus.approval?.visible)            items.push({ path: '/approval',        label: 'Approval',          icon: '✅' });
  if (menus.user_sessions?.visible)       items.push({ path: '/sessions-monitor', label: 'Monitor Sesi',    icon: '📡' });

  // Admin management — hanya jika is_admin
  if (isAdmin) {
    items.push(
      { path: '/users',           label: 'Users',               icon: '👥', divider: true },
      { path: '/roles',           label: 'Roles',               icon: '🔐' },
      { path: '/permissions',     label: 'Permissions',         icon: '🔑' },
      { path: '/unit',            label: 'Unit',                icon: '🏢' },
      { path: '/pegawai',         label: 'Pegawai',             icon: '👨‍💼' },
      { path: '/shift-kelompok',  label: 'Shift Kelompok',      icon: '🔄' },
      { path: '/app-config',      label: 'Konfigurasi Absensi', icon: '⚙️' },
      { path: '/shift-pegawai',   label: 'Shift Pegawai',       icon: '👤' },
      { path: '/roster-upload',   label: 'Roster Upload',       icon: '📄' },
      { path: '/roster-adapter',  label: 'Roster Adapter',      icon: '🧩' },
      { path: '/roster-shift',    label: 'Roster Shift',        icon: '🗓️' },
      { path: '/penilaian-shift', label: 'Penilaian Shift',     icon: '⚖️' },
    );
  }

  items.push({ path: '/login-absensi', label: 'Login Absensi', icon: '🔓', divider: true });
  return items;
};
```

### 7. Repository List & Endpoint Mapping

| Repository | Endpoint Backend |
|---|---|
| `AuthRepository` | `POST /auth/login`, `POST /auth/logout`, `POST /auth/refresh` |
| `UserRepository` | `CRUD /users/` |
| `RoleRepository` | `CRUD /roles/` |
| `PermissionRepository` | `CRUD /permissions/` |
| `PegawaiRepository` | `CRUD /pegawai/` + foto upload |
| `UnitRepository` | `CRUD /unit/` |
| `ShiftKelompokRepository` | `CRUD /shift-kelompok/` |
| `AppConfigRepository` | `GET /app-config/`, `PUT /app-config/` |
| `PegawaiShiftKelompokRepository` | `CRUD /pegawai-shift-kelompok/` + `POST /import` + `GET /template/download` |
| `RosterUploadBatchRepository` | `CRUD /roster-upload-batch/` |
| `RosterShiftRepository` | `CRUD /roster-shift/` + import Excel |
| `PenilaianShiftAbsensiRepository` | `POST /penilaian-shift-absensi/evaluate` |
| `ApprovalRepository` | `CRUD /approval-pengajuan-absensi/` |
| `AbsensiRepository` | `GET /absensi/`, `POST /absensi/check-in`, `PUT /absensi/check-out` |
| `SessionsRepository` | `GET /user-sessions/` |
| `StatsRepository` | `GET /stats/` |

Semua repository adalah **plain object** (bukan class) dengan async functions menggunakan `apiClient`.

### 8. Perhatian Khusus

#### A. AppConfig — Gantikan ShiftKelompokAturan

**TIDAK ADA** `ShiftKelompokAturanRepository`, `useShiftKelompokAturan`, `ShiftKelompokAturanPage`.
Gantikan seluruhnya dengan:

```js
// data/repositories/AppConfigRepository.js
const get = async () => (await apiClient.get('/app-config/')).data;
const update = async (payload) => (await apiClient.put('/app-config/', payload)).data;
export default { get, update };
```

`AppConfigPage` adalah **form settings** (bukan tabel CRUD):
- Load data saat mount dengan `GET /app-config/`
- Field: `grace_telat_menit`, `toleransi_pulang_cepat_menit`, `batas_lembur_menit`,
  `window_mulai_minus_menit`, `window_selesai_plus_menit`, `maks_sesi_per_hari`, `is_lintas_tanggal`
- Submit dengan `PUT /app-config/`

#### B. PegawaiShiftKelompok — tipe_shift Bukan FK

Form create/edit pakai **dropdown 2 pilihan**: `SHIFT` / `NON_SHIFT`.
Tidak ada lookup ke tabel shift_kelompok.

```js
// Payload:
{ id_pegawai: "PEG001", tipe_shift: "SHIFT", effective_start_date: "2025-01-01", ... }

// Template Excel — kolom 2: "tipe_shift * (SHIFT/NON_SHIFT)"
// bukan "shift_kelompok_kode *"
```

### 9. Session Heartbeat

```js
// domain/hooks/useSessionHeartbeat.js
// Ping backend setiap intervalMinutes menit agar session tidak expired
export const useSessionHeartbeat = (intervalMinutes = 5) => {
  const { user } = useAuth();
  const startHeartbeat = () => { /* setInterval → POST /auth/heartbeat atau /user-sessions/heartbeat */ };
  const stopHeartbeat = () => { /* clearInterval */ };
  return { startHeartbeat, stopHeartbeat };
};
```

### 10. Core Constants

```js
// core/constants/config.js
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://192.168.30.21:8000/api/v1',
  TIMEOUT: 30000,
};
export const STORAGE_KEYS = { ACCESS_TOKEN: 'access_token', USER: 'user', SESSION_ID: 'session_id' };
export const PAGINATION = { DEFAULT_PAGE: 1, DEFAULT_LIMIT: 10, PAGE_SIZE_OPTIONS: [10, 25, 50, 100] };
export const DATE_FORMAT = { DISPLAY: 'DD/MM/YYYY', API: 'YYYY-MM-DD', DATETIME: 'DD/MM/YYYY HH:mm:ss', TIME: 'HH:mm' };
export const ABSENSI_STATUS = { HADIR: 'HADIR', SAKIT: 'SAKIT', IZIN: 'IZIN', ALPA: 'ALPA', CUTI: 'CUTI' };
export const PEGAWAI_STATUS = { PNS: 'PNS', PPPK: 'PPPK', KONTRAK: 'KONTRAK', HONORER: 'HONORER' };
export const GENDER = { L: 'Laki-laki', P: 'Perempuan' };
export const APP_META = { NAME: 'RSUD Sulfat Attendance System', SHORT_NAME: 'Absensi RSUD', VERSION: '1.0.0' };
```

### 11. Env

```
VITE_API_BASE_URL=http://192.168.30.21:8000/api/v1
```

### 12. Output Expected

- `npm install && npm run dev` langsung jalan
- Dua jalur login: `/login-admin` (admin) dan `/login-absensi` (pegawai)
- Landing page memilihkan ke dua jalur
- Semua halaman admin terhubung di router dan sidebar dinamis
- **TIDAK ADA** `ShiftKelompokAturanPage/Repository/Hook`
- **ADA** `AppConfigPage`, `AppConfigRepository`, `useAppConfig`
- `PegawaiShiftKelompokPage` pakai dropdown `tipe_shift` (SHIFT / NON_SHIFT)
- Struktur folder persis sesuai tree di atas

Buatkan dengan struktur lengkap, jangan skip file apapun!
```

---

## ✅ Checklist Hasil

- [ ] Struktur folder sesuai tree di atas
- [ ] `vite.config.js` dengan `--host 0.0.0.0` di script dev
- [ ] API client + interceptor (auto-refresh via cookie + `auth:user-refreshed` event)
- [ ] `AuthContext`: login, logout, isAuthenticated, hasRole, isAdmin, sync dari event
- [ ] RBAC sidebar dari `menu_guard.menus.*.visible` + `menu_guard.is_admin` (bukan hardcode)
- [ ] `PrivateRoute` (admin) + `AttendancePrivateRoute` (pegawai)
- [ ] Landing page + `AdminLoginPage` + `AttendanceLoginPage`
- [ ] Session heartbeat (`useSessionHeartbeat` + `SessionHeartbeatRunner` di App.jsx)
- [ ] `AppConfigRepository` + `useAppConfig` + `AppConfigPage` (form GET+PUT) ✅
- [ ] **TIDAK ADA** `ShiftKelompokAturanRepository/Page/Hook` ❌
- [ ] `PegawaiShiftKelompokPage` pakai `tipe_shift: SHIFT|NON_SHIFT` (dropdown, bukan FK)
- [ ] Semua 16 repository sesuai tabel endpoint mapping
- [ ] Layout responsive: hamburger mobile + fixed sidebar desktop
- [ ] Tailwind setup (`tailwind.config.js`, `postcss.config.js`, `@tailwind` di `index.css`)

---

## 🔑 Poin Kritis

1. **menu_guard dari backend** — sidebar dibangun dari `menu_guard.menus.*.visible`, jangan hardcode
2. **AppConfig singleton** — satu form GET/PUT, tidak ada list/create/delete/table
3. **tipe_shift** — dropdown 2 pilihan saja, tidak perlu lookup ke tabel `shift_kelompok`
4. **withCredentials: true** — wajib di axios untuk refresh token via httpOnly cookie
5. **`auth:user-refreshed` event** — AuthContext harus listen event ini agar state sync setelah auto-refresh
6. **Session heartbeat** — aktif saat user login, berhenti saat logout

---

**Happy Coding! 🚀**