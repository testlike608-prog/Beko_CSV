import { useState, useEffect, useRef } from "react";

const NAV_ITEMS = [
  { id: "home", label: "Home", icon: "⌂", roles: ["admin", "user", "dev"] },
  { id: "create_program", label: "Create Program CSV", icon: "⊞", roles: ["admin", "dev"] },
  { id: "sql", label: "SQL Connection", icon: "◈", roles: ["admin", "user", "dev"] },
  { id: "create_user", label: "Create New User", icon: "⊕", roles: ["admin", "dev"] },
];

const FIXED_OPTIONS = {
  front_logo: [["None","00"],["Beko","1A"],["Defy","1B"],["Arcelik","1C"],["Ariston","1D"],["Whirlpool","1E"]],
  display_logo: [["None","00"],["Fish screen","1F"],["Second screen","1G"],["Ahmed screen","1H"],["Opt3","1I"],["Opt4","1J"]],
  color: [["None","00"],["White","6A"],["Black","6B"],["Opt3","6C"],["Opt4","6D"],["Opt5","6E"]],
  data_logo: [["None","00"],["Beko","4A"],["Defy","4B"],["Arcelik","4C"],["Ariston","4D"],["Whirlpool","4E"]],
  inverter_logo: [["None","00"],["Beko","7A"],["Defy","7B"],["Arcelik","7C"],["Ariston","7D"],["Whirlpool","7E"]],
  power_logo: [["None","00"],["Beko","3A"],["Defy","3B"],["Arcelik","3C"],["Ariston","3D"],["Whirlpool","3E"]],
  eva_cover: [["None","00"],["Beko","2A"],["Defy","2B"],["Arcelik","2C"],["Ariston","2D"],["Whirlpool","2E"]],
  drawer_printing: [["None","00"],["Veg","5A"],["Dairy","5B"],["Meat","5C"],["Opt3","5D"],["Opt5","5E"]],
  color_logo: [["None","00"],["White","6A"],["Black","6B"],["Opt3","6C"],["Opt4","6D"],["Opt5","6E"]],
  fan_cover: [["None","00"],["Beko","8A"],["Defy","8B"],["Arcelik","8C"],["Ariston","8D"],["Whirlpool","8E"]],
  shelve_color: [["None","00"],["White","9A"],["Black","9B"],["Opt3","9C"],["Opt4","9D"],["Opt5","9E"]],
};

const FIELD_LABELS = {
  front_logo: "Front Logo", display_logo: "Display Logo", color: "Color",
  data_logo: "Data Logo", inverter_logo: "Inverter Logo", power_logo: "Power Logo",
  eva_cover: "Eva Cover", drawer_printing: "Drawer Printing", color_logo: "Color Logo",
  fan_cover: "Fan Cover", shelve_color: "Shelve Color",
};

function Toast({ msg, type, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 2500);
    return () => clearTimeout(t);
  }, [msg]);
  if (!msg) return null;
  const bg = type === "success" ? "#e6f9f0" : "#fef2f2";
  const color = type === "success" ? "#065f46" : "#991b1b";
  const border = type === "success" ? "#6ee7b7" : "#fca5a5";
  return (
    <div style={{
      position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)",
      background: bg, color, border: `1px solid ${border}`, borderRadius: 12,
      padding: "10px 20px", fontWeight: 500, fontSize: 14, zIndex: 9999,
      boxShadow: "0 4px 20px rgba(0,0,0,0.08)", minWidth: 200, textAlign: "center"
    }}>
      {msg}
    </div>
  );
}

function Badge({ children, variant = "idle" }) {
  const styles = {
    pass: { bg: "#dcfce7", color: "#166534", dot: "#16a34a" },
    fail: { bg: "#fee2e2", color: "#991b1b", dot: "#dc2626" },
    idle: { bg: "#f3f4f6", color: "#6b7280", dot: "#9ca3af" },
    arrived: { bg: "#dbeafe", color: "#1e40af", dot: "#2563eb" },
    waiting: { bg: "#fef9c3", color: "#854d0e", dot: "#ca8a04" },
    connected: { bg: "#dcfce7", color: "#166534", dot: "#16a34a" },
    disconnected: { bg: "#fee2e2", color: "#991b1b", dot: "#dc2626" },
  };
  const s = styles[variant] || styles.idle;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 12px",
      borderRadius: 99, background: s.bg, color: s.color, fontSize: 13, fontWeight: 500
    }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: s.dot, flexShrink: 0 }} />
      {children}
    </span>
  );
}

function StationCard({ title, ip, arrivedState, resultState, dummyNum, skuNum }) {
  return (
    <div style={{
      background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
      borderRadius: "var(--border-radius-lg)", padding: "1.25rem 1.5rem", marginBottom: 16
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <span style={{ fontWeight: 500, fontSize: 16 }}>{title}</span>
        <span style={{ fontSize: 12, color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)" }}>{ip}</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 6 }}>Fridge arrived</div>
          <Badge variant={arrivedState}>{arrivedState === "arrived" ? "Fridge arrived" : "Waiting..."}</Badge>
        </div>
        <div>
          <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 6 }}>Test result</div>
          <Badge variant={resultState === "PASS" ? "pass" : resultState === "FAIL" ? "fail" : "idle"}>
            {resultState || "No result yet"}
          </Badge>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {[["Dummy number", dummyNum], ["SKU number", skuNum]].map(([lbl, val]) => (
          <div key={lbl} style={{
            background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-md)",
            padding: "8px 12px", display: "flex", flexDirection: "column", gap: 2
          }}>
            <span style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>{lbl}</span>
            <span style={{
              fontFamily: "var(--font-mono)", fontWeight: 500, fontSize: 15,
              color: val ? "var(--color-text-primary)" : "var(--color-text-tertiary)"
            }}>{val || "—"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SelectPicker({ fieldKey, label, value, options, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef();
  useEffect(() => {
    const fn = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", fn);
    return () => document.removeEventListener("mousedown", fn);
  }, []);
  const selected = options.find(o => o[0] === value);
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "10px 14px", borderRadius: "var(--border-radius-md)",
          border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-primary)",
          cursor: "pointer", color: "var(--color-text-primary)", fontSize: 14
        }}
      >
        <span>{label}</span>
        <span style={{
          fontSize: 12, padding: "2px 8px", borderRadius: 6, marginLeft: 8,
          background: selected ? "var(--color-background-info)" : "var(--color-background-secondary)",
          color: selected ? "var(--color-text-info)" : "var(--color-text-tertiary)"
        }}>
          {selected ? selected[0] : "Select…"}
        </span>
      </button>
      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0, zIndex: 100,
          background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-secondary)",
          borderRadius: "var(--border-radius-lg)", boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
          maxHeight: 220, overflowY: "auto"
        }}>
          {options.map(([name, code]) => (
            <button
              key={code}
              type="button"
              onClick={() => { onChange(name, code); setOpen(false); }}
              style={{
                width: "100%", padding: "9px 14px", display: "flex", justifyContent: "space-between",
                alignItems: "center", border: "none", background: name === value ? "var(--color-background-secondary)" : "transparent",
                cursor: "pointer", color: "var(--color-text-primary)", fontSize: 14, textAlign: "left"
              }}
            >
              <span>{name}</span>
              <span style={{ fontSize: 11, color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)" }}>{code}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Modal({ open, title, onClose, children }) {
  if (!open) return null;
  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 16
    }}>
      <div style={{
        background: "var(--color-background-primary)", borderRadius: "var(--border-radius-lg)",
        border: "0.5px solid var(--color-border-secondary)", width: "100%", maxWidth: 560,
        maxHeight: "90vh", overflowY: "auto", padding: "1.5rem"
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <span style={{ fontWeight: 500, fontSize: 17 }}>{title}</span>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 20, color: "var(--color-text-secondary)" }}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function HomePage({ auth }) {
  const s1 = { arrivedState: "waiting", resultState: null, dummyNum: null, skuNum: null };
  const s2 = { arrivedState: "arrived", resultState: "PASS", dummyNum: "D-4892", skuNum: "WMT-1234" };
  const savedPrograms = [
    { name: "Beko_WMT1234.csv", kb: 2.1 },
    { name: "Ariston_FRG22.csv", kb: 1.8 },
    { name: "Whirlpool_WF8.csv", kb: 2.4 },
    { name: "Defy_456.csv", kb: 1.5 },
  ];
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>System Overview</h2>
        <p style={{ color: "var(--color-text-secondary)", fontSize: 14 }}>Refrigerator vision inspection — live station status</p>
      </div>
      <StationCard title="Outer station" ip="192.168.1.16:7940" {...s1} />
      <StationCard title="Inner station" ip="192.168.1.17:7950" {...s2} />
      {savedPrograms.length > 0 && (
        <div style={{
          background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
          borderRadius: "var(--border-radius-lg)", padding: "1.25rem"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
            <span style={{ fontWeight: 500 }}>Saved programs</span>
            <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Newest first</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 8 }}>
            {savedPrograms.map(f => (
              <button key={f.name} style={{
                padding: "10px 12px", border: "0.5px solid var(--color-border-tertiary)",
                borderRadius: "var(--border-radius-md)", background: "var(--color-background-secondary)",
                textAlign: "left", cursor: "pointer", color: "var(--color-text-primary)"
              }}>
                <div style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</div>
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 2 }}>{f.kb} KB</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CreateProgramPage({ setToast }) {
  const fields = Object.keys(FIELD_LABELS);
  const [values, setValues] = useState({});
  const [modelName, setModelName] = useState("");
  const [sku, setSku] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSelect = (field, name) => {
    setValues(v => ({ ...v, [field]: name }));
  };

  const handleSubmit = e => {
    e.preventDefault();
    if (!modelName.trim()) return setToast({ msg: "Please enter model name", type: "error" });
    if (!sku.trim()) return setToast({ msg: "Please enter SKU", type: "error" });
    for (const f of fields) {
      if (!values[f]) return setToast({ msg: `Please select: ${FIELD_LABELS[f]}`, type: "error" });
    }
    setSubmitted(true);
    setToast({ msg: "Program created successfully", type: "success" });
  };

  const handleReset = () => {
    setValues({});
    setModelName("");
    setSku("");
    setSubmitted(false);
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>Create Program CSV</h2>
        <p style={{ color: "var(--color-text-secondary)", fontSize: 14 }}>Configure and generate a new product program file</p>
      </div>
      <form onSubmit={handleSubmit}>
        <div style={{
          background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
          borderRadius: "var(--border-radius-lg)", padding: "1.5rem", marginBottom: 16
        }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
            <div>
              <label style={{ display: "block", fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                Model name <span style={{ color: "#e24b4a" }}>*</span>
              </label>
              <input
                value={modelName}
                onChange={e => setModelName(e.target.value)}
                placeholder="beko"
                style={{ width: "100%", padding: "10px 14px", borderRadius: "var(--border-radius-md)", border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-primary)", color: "var(--color-text-primary)", fontSize: 14, boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                SKU <span style={{ color: "#e24b4a" }}>*</span>
              </label>
              <input
                value={sku}
                onChange={e => setSku(e.target.value)}
                placeholder="WMT-1234"
                style={{ width: "100%", padding: "10px 14px", borderRadius: "var(--border-radius-md)", border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-primary)", color: "var(--color-text-primary)", fontSize: 14, boxSizing: "border-box" }}
              />
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {fields.map(field => (
              <SelectPicker
                key={field}
                fieldKey={field}
                label={FIELD_LABELS[field]}
                value={values[field]}
                options={FIXED_OPTIONS[field]}
                onChange={(name) => handleSelect(field, name)}
              />
            ))}
          </div>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <button type="submit" style={{
            flex: 3, padding: "12px 0", borderRadius: "var(--border-radius-md)",
            background: "#16a34a", color: "#fff", fontWeight: 500, fontSize: 15, border: "none", cursor: "pointer"
          }}>
            Create program
          </button>
          <button type="button" onClick={handleReset} style={{
            flex: 1, padding: "12px 0", borderRadius: "var(--border-radius-md)",
            background: "#dc2626", color: "#fff", fontWeight: 500, fontSize: 14, border: "none", cursor: "pointer"
          }}>
            Reset
          </button>
        </div>
      </form>
      {submitted && (
        <div style={{
          marginTop: 16, background: "var(--color-background-success)", border: "0.5px solid var(--color-border-success)",
          borderRadius: "var(--border-radius-lg)", padding: "1.25rem"
        }}>
          <div style={{ color: "var(--color-text-success)", fontWeight: 500, marginBottom: 8 }}>Program created</div>
          <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
            SKU: <code style={{ fontFamily: "var(--font-mono)" }}>{sku}</code> &nbsp;·&nbsp;
            Model: <code style={{ fontFamily: "var(--font-mono)" }}>{modelName}</code>
          </div>
        </div>
      )}
    </div>
  );
}

function SQLPage({ setToast }) {
  const [form, setForm] = useState({ server1: "", db1: "", server2: "", db2: "", auth: "", login: "", password: "" });
  const [db1Connected, setDb1Connected] = useState(false);
  const [db2Connected, setDb2Connected] = useState(false);

  const handleSubmit = e => {
    e.preventDefault();
    if (!form.server1 || !form.db1) return setToast({ msg: "Please fill in all required fields", type: "error" });
    setDb1Connected(true);
    setDb2Connected(!!form.server2);
    setToast({ msg: "Connection saved successfully", type: "success" });
  };

  const handleReset = () => {
    setForm({ server1: "", db1: "", server2: "", db2: "", auth: "", login: "", password: "" });
    setDb1Connected(false);
    setDb2Connected(false);
  };

  const inp = { width: "100%", padding: "10px 14px", borderRadius: "var(--border-radius-md)", border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-primary)", color: "var(--color-text-primary)", fontSize: 14, boxSizing: "border-box" };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>SQL connection</h2>
        <p style={{ color: "var(--color-text-secondary)", fontSize: 14 }}>Configure database connections for both stations</p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 16, alignItems: "start" }}>
        <form onSubmit={handleSubmit}>
          <div style={{
            background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
            borderRadius: "var(--border-radius-lg)", padding: "1.5rem"
          }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              {[
                ["server1", "Server 1 name", "Server, Port"],
                ["db1", "Database 1", "Database name"],
                ["server2", "Server 2 name", "Server, Port"],
                ["db2", "Database 2", "Database name"],
              ].map(([key, label, ph]) => (
                <div key={key}>
                  <label style={{ display: "block", fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 6 }}>{label}</label>
                  <input value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} placeholder={ph} style={inp} />
                </div>
              ))}
              <div>
                <label style={{ display: "block", fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 6 }}>Authentication</label>
                <select value={form.auth} onChange={e => setForm(f => ({ ...f, auth: e.target.value }))} style={{ ...inp }}>
                  <option value="">-- Choose --</option>
                  <option value="windows">Windows authentication</option>
                  <option value="sql">SQL server authentication</option>
                </select>
              </div>
              <div>
                <label style={{ display: "block", fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 6 }}>Login</label>
                <input value={form.login} onChange={e => setForm(f => ({ ...f, login: e.target.value }))} placeholder="Username" disabled={form.auth === "windows"} style={{ ...inp, opacity: form.auth === "windows" ? 0.5 : 1 }} />
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={{ display: "block", fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 6 }}>Password</label>
                <input type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} placeholder="Password" disabled={form.auth === "windows"} style={{ ...inp, opacity: form.auth === "windows" ? 0.5 : 1 }} />
              </div>
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
              <button type="submit" style={{ flex: 1, padding: "11px 0", borderRadius: "var(--border-radius-md)", background: "#2563eb", color: "#fff", fontWeight: 500, fontSize: 14, border: "none", cursor: "pointer" }}>
                Submit
              </button>
              <button type="button" onClick={handleReset} style={{ flex: 1, padding: "11px 0", borderRadius: "var(--border-radius-md)", background: "#dc2626", color: "#fff", fontWeight: 500, fontSize: 14, border: "none", cursor: "pointer" }}>
                Reset
              </button>
            </div>
          </div>
        </form>
        <div style={{
          background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
          borderRadius: "var(--border-radius-lg)", padding: "1.25rem"
        }}>
          <div style={{ fontWeight: 500, marginBottom: 14, color: "#1e6fb5" }}>Connection status</div>
          {[["Database 1", db1Connected], ["Database 2", db2Connected]].map(([label, conn]) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <span style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>{label}</span>
              <Badge variant={conn ? "connected" : "disconnected"}>{conn ? "Connected" : "Disconnected"}</Badge>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CreateUserPage({ setToast }) {
  const [form, setForm] = useState({ username: "", password: "", auth: "" });
  const [done, setDone] = useState(false);

  const handleSubmit = e => {
    e.preventDefault();
    if (!form.username || !form.password || !form.auth) {
      return setToast({ msg: "Please fill in all fields", type: "error" });
    }
    setDone(true);
    setToast({ msg: `User "${form.username}" created`, type: "success" });
    setForm({ username: "", password: "", auth: "" });
    setTimeout(() => setDone(false), 3000);
  };

  const inp = { width: "100%", padding: "11px 14px", borderRadius: "var(--border-radius-md)", border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-primary)", color: "var(--color-text-primary)", fontSize: 14, boxSizing: "border-box" };

  return (
    <div style={{ maxWidth: 420 }}>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>Create new user</h2>
        <p style={{ color: "var(--color-text-secondary)", fontSize: 14 }}>Add a user account to the system</p>
      </div>
      <div style={{
        background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
        borderRadius: "var(--border-radius-lg)", padding: "1.5rem"
      }}>
        {done && (
          <div style={{ background: "var(--color-background-success)", border: "0.5px solid var(--color-border-success)", borderRadius: "var(--border-radius-md)", padding: "10px 14px", marginBottom: 16, color: "var(--color-text-success)", fontSize: 14, fontWeight: 500 }}>
            User created successfully
          </div>
        )}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ display: "block", fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 6 }}>Username</label>
            <input value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} placeholder="Enter username" style={inp} />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 6 }}>Password</label>
            <input type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} placeholder="Enter password" style={inp} />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 6 }}>Role</label>
            <select value={form.auth} onChange={e => setForm(f => ({ ...f, auth: e.target.value }))} style={inp}>
              <option value="">-- Choose role --</option>
              <option value="admin">Admin</option>
              <option value="user">User</option>
            </select>
          </div>
          <button type="submit" style={{ padding: "12px 0", borderRadius: "var(--border-radius-md)", background: "#2563eb", color: "#fff", fontWeight: 500, fontSize: 15, border: "none", cursor: "pointer", marginTop: 4 }}>
            Add user
          </button>
        </form>
      </div>
    </div>
  );
}

function LoginPage({ onLogin }) {
  const [form, setForm] = useState({ username: "", password: "" });
  const [showPw, setShowPw] = useState(false);
  const [err, setErr] = useState("");

  const handleSubmit = e => {
    e.preventDefault();
    if (!form.username || !form.password) return setErr("Please fill in all fields");
    if (form.password.length < 3) return setErr("Invalid credentials");
    const role = form.username === "admin" ? "admin" : form.username === "dev" ? "dev" : "user";
    onLogin({ username: form.username, role });
  };

  const inp = { width: "100%", padding: "13px 16px", borderRadius: "var(--border-radius-lg)", border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-secondary)", color: "var(--color-text-primary)", fontSize: 15, boxSizing: "border-box" };

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "linear-gradient(135deg, #0f2027 0%, #203a43 40%, #2c5364 100%)"
    }}>
      <div style={{
        background: "rgba(255,255,255,0.06)", backdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.12)", borderRadius: 24,
        padding: "40px 36px", width: "100%", maxWidth: 380, position: "relative", overflow: "hidden"
      }}>
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 4, background: "linear-gradient(90deg, #00c6ff, #0072ff, #00c6ff)", backgroundSize: "200% 100%", animation: "slide 3s linear infinite" }} />
        <div style={{ width: 60, height: 60, borderRadius: "50%", background: "linear-gradient(135deg,#00c6ff,#0072ff)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px", color: "#fff", fontSize: 22, fontWeight: 500 }}>M</div>
        <h1 style={{ textAlign: "center", color: "#fff", fontSize: 24, fontWeight: 500, marginBottom: 4 }}>Welcome back</h1>
        <p style={{ textAlign: "center", color: "#a7b5c2", fontSize: 14, marginBottom: 28 }}>Sign in to your account</p>
        {err && (
          <div style={{ background: "rgba(255,77,77,0.15)", color: "#ff8080", padding: "10px 14px", borderRadius: 10, border: "1px solid rgba(255,77,77,0.3)", marginBottom: 16, fontSize: 14 }}>
            {err}
          </div>
        )}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div>
            <label style={{ display: "block", fontSize: 13, color: "#cfd9e3", marginBottom: 7 }}>Username</label>
            <input value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} placeholder="Enter your username" style={{ ...inp, background: "rgba(255,255,255,0.08)", borderColor: "rgba(255,255,255,0.15)", color: "#f1f1f1" }} />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 13, color: "#cfd9e3", marginBottom: 7 }}>Password</label>
            <div style={{ position: "relative" }}>
              <input type={showPw ? "text" : "password"} value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} placeholder="Enter your password" style={{ ...inp, background: "rgba(255,255,255,0.08)", borderColor: "rgba(255,255,255,0.15)", color: "#f1f1f1", paddingRight: 60 }} />
              <button type="button" onClick={() => setShowPw(v => !v)} style={{ position: "absolute", right: 14, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", color: "#00c6ff", fontSize: 11, fontWeight: 500, cursor: "pointer", letterSpacing: 0.5 }}>
                {showPw ? "HIDE" : "SHOW"}
              </button>
            </div>
          </div>
          <button type="submit" style={{ padding: "13px 0", borderRadius: 12, background: "linear-gradient(90deg,#00c6ff,#0072ff)", color: "#fff", fontWeight: 500, fontSize: 15, border: "none", cursor: "pointer", marginTop: 4 }}>
            Sign in
          </button>
        </form>
        <style>{`@keyframes slide{0%{background-position:0 0}100%{background-position:200% 0}}`}</style>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [activePage, setActivePage] = useState("home");
  const [toast, setToast] = useState({ msg: "", type: "success" });
  const [timesModalOpen, setTimesModalOpen] = useState(false);
  const [alertModal, setAlertModal] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => {
      if (user && Math.random() > 0.7) {
        setAlertModal({ station: "outer", type: "scanner" });
      }
    }, 8000);
    return () => clearTimeout(t);
  }, [user]);

  if (!user) {
    return <LoginPage onLogin={u => { setUser(u); setActivePage("home"); }} />;
  }

  const allowedNav = NAV_ITEMS.filter(n => n.roles.includes(user.role));

  const renderPage = () => {
    switch (activePage) {
      case "home": return <HomePage auth={user.role} />;
      case "create_program": return <CreateProgramPage setToast={setToast} />;
      case "sql": return <SQLPage setToast={setToast} />;
      case "create_user": return <CreateUserPage setToast={setToast} />;
      default: return <HomePage auth={user.role} />;
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--color-background-tertiary)" }}>
      <header style={{
        background: "var(--color-background-primary)", borderBottom: "0.5px solid var(--color-border-tertiary)",
        padding: "0 2rem", height: 64, display: "flex", alignItems: "center", justifyContent: "space-between"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 36, height: 36, borderRadius: "50%", background: "linear-gradient(135deg,#00c6ff,#0072ff)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 500, fontSize: 16 }}>M</div>
          <div>
            <div style={{ fontWeight: 500, fontSize: 15 }}>Refrigerator Vision System</div>
            <div style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>Meeserv</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
            {user.username} · <span style={{ textTransform: "capitalize" }}>{user.role}</span>
          </span>
          <button onClick={() => setUser(null)} style={{ fontSize: 13, color: "#2563eb", background: "none", border: "none", cursor: "pointer", fontWeight: 500 }}>
            Logout
          </button>
        </div>
      </header>

      <div style={{ display: "flex", maxWidth: 1100, margin: "0 auto", padding: "24px 20px", gap: 20 }}>
        <aside style={{ width: 220, flexShrink: 0 }}>
          <nav style={{
            background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
            borderRadius: "var(--border-radius-lg)", padding: "8px", position: "sticky", top: 24
          }}>
            {allowedNav.map(item => (
              <button
                key={item.id}
                onClick={() => setActivePage(item.id)}
                style={{
                  width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "10px 12px", borderRadius: "var(--border-radius-md)", marginBottom: 2,
                  background: activePage === item.id ? "var(--color-background-secondary)" : "transparent",
                  border: activePage === item.id ? "0.5px solid var(--color-border-secondary)" : "0.5px solid transparent",
                  cursor: "pointer", color: "var(--color-text-primary)", fontSize: 14, textAlign: "left"
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 15, opacity: 0.7 }}>{item.icon}</span>
                  <span style={{ fontWeight: activePage === item.id ? 500 : 400 }}>{item.label}</span>
                </span>
                <span style={{ color: "var(--color-text-tertiary)", fontSize: 14 }}>›</span>
              </button>
            ))}
            {user.role === "admin" || user.role === "dev" ? (
              <button
                onClick={() => setTimesModalOpen(true)}
                style={{
                  width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "10px 12px", borderRadius: "var(--border-radius-md)", marginBottom: 2,
                  background: "transparent", border: "0.5px solid transparent",
                  cursor: "pointer", color: "var(--color-text-primary)", fontSize: 14, textAlign: "left"
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 15, opacity: 0.7 }}>◎</span>
                  <span>Adjust times</span>
                </span>
                <span style={{ color: "var(--color-text-tertiary)", fontSize: 14 }}>›</span>
              </button>
            ) : null}
            <div style={{ borderTop: "0.5px solid var(--color-border-tertiary)", margin: "8px 0" }} />
            <button
              onClick={() => setUser(null)}
              style={{ width: "100%", padding: "10px 12px", borderRadius: "var(--border-radius-md)", background: "transparent", border: "none", cursor: "pointer", color: "#2563eb", fontSize: 14, textAlign: "left", fontWeight: 500 }}
            >
              Logout
            </button>
          </nav>
        </aside>

        <main style={{ flex: 1, minWidth: 0 }}>
          {renderPage()}
        </main>
      </div>

      <Modal open={timesModalOpen} title="Adjust time settings" onClose={() => setTimesModalOpen(false)}>
        {[
          ["Socket timeouts", [["Device connect (s)", 5], ["Device receive (s)", 1], ["Client socket (s)", 1]]],
          ["Reconnection delays", [["Initial retry base (s)", 0.5], ["Max backoff (s)", 30], ["Check interval (s)", 1]]],
          ["Web interface (ms)", [["Status refresh", 1500], ["Log polling", 800], ["Server4 refresh", 2000]]],
        ].map(([section, fields]) => (
          <div key={section} style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-secondary)", borderBottom: "0.5px solid var(--color-border-tertiary)", paddingBottom: 6, marginBottom: 12 }}>{section}</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {fields.map(([label, def]) => (
                <div key={label}>
                  <label style={{ display: "block", fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 5 }}>{label}</label>
                  <input type="number" defaultValue={def} style={{ width: "100%", padding: "8px 12px", borderRadius: "var(--border-radius-md)", border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-secondary)", color: "var(--color-text-primary)", fontSize: 14, boxSizing: "border-box" }} />
                </div>
              ))}
            </div>
          </div>
        ))}
        <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
          <button onClick={() => { setTimesModalOpen(false); setToast({ msg: "Settings saved", type: "success" }); }} style={{ flex: 1, padding: "11px 0", borderRadius: "var(--border-radius-md)", background: "#2563eb", color: "#fff", fontWeight: 500, fontSize: 14, border: "none", cursor: "pointer" }}>
            Save settings
          </button>
          <button onClick={() => setTimesModalOpen(false)} style={{ flex: 1, padding: "11px 0", borderRadius: "var(--border-radius-md)", background: "transparent", border: "0.5px solid var(--color-border-secondary)", cursor: "pointer", color: "var(--color-text-primary)", fontSize: 14 }}>
            Cancel
          </button>
        </div>
      </Modal>

      <Modal open={!!alertModal} title="" onClose={() => setAlertModal(null)}>
        {alertModal && (
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}> </div>
            <div style={{ color: "#dc2626", fontWeight: 500, fontSize: 18, marginBottom: 8 }}>System alert</div>
            <p style={{ color: "var(--color-text-secondary)", marginBottom: 20 }}>
              Auto scanning failed in {alertModal.station} station
            </p>
            <input placeholder="Scan or enter code manually" style={{ width: "100%", padding: "11px 14px", borderRadius: "var(--border-radius-md)", border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-secondary)", color: "var(--color-text-primary)", fontSize: 14, boxSizing: "border-box", marginBottom: 12 }} />
            <button onClick={() => { setAlertModal(null); setToast({ msg: "Data submitted", type: "success" }); }} style={{ width: "100%", padding: "12px 0", borderRadius: "var(--border-radius-md)", background: "#2563eb", color: "#fff", fontWeight: 500, fontSize: 14, border: "none", cursor: "pointer" }}>
              OK / Confirm
            </button>
          </div>
        )}
      </Modal>

      <Toast msg={toast.msg} type={toast.type} onClose={() => setToast({ msg: "", type: "success" })} />
    </div>
  );
}
