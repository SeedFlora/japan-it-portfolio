import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Activity, ArrowDownLeft, ArrowRightLeft, ArrowUpRight, Check, ChevronRight, ClipboardCheck, Download, Globe2, Layers3, LayoutDashboard, LoaderCircle, Package, Plus, RefreshCw, Search, ShieldCheck, Truck, X } from 'lucide-react';

type Language = 'en' | 'ja';
type Role = 'viewer' | 'operator' | 'manager';
type Section = 'overview' | 'inventory' | 'movements' | 'requests' | 'audit';
type Kind = 'receive' | 'issue' | 'transfer';
type Product = { id: number; sku: string; name_en: string; name_ja: string; category: string; unit: string; reorder_point: number; balances: Record<string, number>; total: number; low_stock: boolean };
type StockMovement = { id: string; kind: Kind; product_id: number; quantity: number; from_location: string | null; to_location: string | null; reference: string; actor: string; created_at: string };
type StockRequest = { id: string; product_id: number; quantity: number; location: string; note: string; status: 'open' | 'approved' | 'rejected' | 'received'; created_by: string; created_at: string };
type AuditEvent = { id: number; event: string; entity_id: string; actor: string; detail: string; created_at: string };
type State = { products: Product[]; locations: { id: string; name_en: string; name_ja: string }[]; movements: StockMovement[]; requests: StockRequest[]; audit: AuditEvent[]; summary: { active_skus: number; low_stock: number; pending_requests: number; movement_count: number }; generated_at: string };
type Dialog = 'movement' | 'request' | null;

const copy = {
  en: {
    overview: 'Overview', inventory: 'Inventory', movements: 'Stock movements', requests: 'Replenishment', audit: 'Audit trail',
    tagline: 'A clearer view of every movement.', demo: 'Portfolio demo · synthetic data', demoNote: 'Roles are simulated. This demo does not authenticate users.',
    viewer: 'Planning · view only', operator: 'Warehouse · operator', manager: 'Operations · manager', workspace: 'WORKSPACE',
    pageTitle: 'Warehouse control', pageSubtitle: 'Stock, approvals and decisions in one place.', active: 'Active SKUs', low: 'Below reorder point', pending: 'Awaiting approval', totalMovements: 'Recorded movements',
    updated: 'Updated', refresh: 'Refresh', addMovement: 'Record movement', addRequest: 'Request stock', export: 'Export CSV',
    distribution: 'Stock across locations', distributionNote: 'Quantities are compared within each SKU; units differ between products.', recent: 'Recent activity', viewAll: 'View all', attention: 'Needs attention', attentionNote: 'Total stock below the product reorder point.',
    search: 'Search SKU or product…', allStock: 'All stock', lowOnly: 'Low stock only', sku: 'SKU / PRODUCT', main: 'Main warehouse', dispatch: 'Dispatch hub', total: 'TOTAL', reorder: 'REORDER POINT', status: 'STATUS', healthy: 'Available', lowBadge: 'Low stock', unit: 'unit', noResults: 'No matching records.',
    product: 'Product', quantity: 'Quantity', source: 'From location', destination: 'To location', reference: 'Reference', movementType: 'Movement type', receive: 'Receive', issue: 'Dispatch', transfer: 'Transfer', cancel: 'Cancel', save: 'Save movement', createRequest: 'Create request', note: 'Reason / note', location: 'Location',
    saveNote: 'A retry of the same movement uses the same idempotency key. Stock and audit entries commit together.', requestNote: 'Creating a request does not change stock. A manager must approve it before receipt.',
    success: 'Saved. The latest stock and audit trail are shown below.', replayed: 'This operation was already saved. No stock was added or removed twice.', approval: 'Approve', reject: 'Reject', receiveApproved: 'Receive approved stock', open: 'Awaiting approval', approved: 'Approved', rejected: 'Rejected', received: 'Received',
    action: 'ACTION', time: 'TIME', route: 'ROUTE', actor: 'RECORDED BY', event: 'EVENT', entity: 'RECORD', details: 'DETAILS', readOnly: 'Switch to the operator role to record stock or request replenishment.', managerHint: 'Switch to the manager role to approve or reject open requests.',
    connection: 'Could not connect to the API. Start the backend and retry.', loading: 'Loading warehouse…', footer: 'Built by Budi Juarto · React / TypeScript / FastAPI / SQLite',
    insufficient_stock: 'Not enough stock at the source location. Nothing was changed.', idempotency_conflict: 'This retry key was used with different data. Close this dialog and start a new movement.', invalid_locations: 'Choose valid, different source and destination locations.', unknown_location: 'Location not found.', unknown_product: 'Product not found.', read_only: 'This role cannot change stock.', manager_required: 'A manager must make this decision.', approval_required: 'Approve the request before receiving stock.', request_state_conflict: 'This request has already changed. Refresh and check its current status.', database_unavailable: 'The database could not finish the operation. Retry the same operation.', invalidInput: 'Check the quantity, locations and reference. Quantity must be a positive whole number.', failed: 'The operation could not be completed. Please retry.',
  },
  ja: {
    overview: '概要', inventory: '在庫一覧', movements: '入出庫履歴', requests: '補充申請', audit: '監査ログ',
    tagline: 'すべての入出庫を、より明確に。', demo: 'ポートフォリオデモ・架空データ', demoNote: '権限はデモ用です。ユーザー認証は実装していません。',
    viewer: '計画担当・閲覧のみ', operator: '倉庫担当・作業者', manager: '運営担当・管理者', workspace: 'ワークスペース',
    pageTitle: '倉庫管理', pageSubtitle: '在庫・承認・判断をひとつの画面で。', active: '登録SKU数', low: '発注点未満', pending: '承認待ち', totalMovements: '入出庫記録数',
    updated: '更新', refresh: '更新', addMovement: '入出庫を記録', addRequest: '補充を申請', export: 'CSV出力',
    distribution: '拠点別在庫', distributionNote: '数量はSKU内で比較します。商品によって単位が異なります。', recent: '最近の入出庫', viewAll: 'すべて見る', attention: '補充が必要な商品', attentionNote: '商品合計在庫が発注点を下回っています。',
    search: 'SKU・商品名で検索…', allStock: 'すべての在庫', lowOnly: '在庫不足のみ', sku: 'SKU / 商品', main: '本倉庫', dispatch: '出荷拠点', total: '合計', reorder: '発注点', status: '状態', healthy: '在庫あり', lowBadge: '在庫不足', unit: '単位', noResults: '該当する記録がありません。',
    product: '商品', quantity: '数量', source: '移動元拠点', destination: '移動先拠点', reference: '伝票・参照番号', movementType: '処理区分', receive: '入庫', issue: '出庫', transfer: '拠点間移動', cancel: 'キャンセル', save: '入出庫を保存', createRequest: '補充申請を作成', note: '申請理由・備考', location: '拠点',
    saveNote: '同じ処理の再試行には同じキーを使用します。在庫と監査ログは同時に確定します。', requestNote: '申請時には在庫は変わりません。入庫する前に管理者の承認が必要です。',
    success: '保存しました。最新の在庫と監査ログを表示しています。', replayed: 'この処理は保存済みです。在庫の二重更新は発生していません。', approval: '承認', reject: '却下', receiveApproved: '承認済みの在庫を入庫', open: '承認待ち', approved: '承認済み', rejected: '却下', received: '入庫済み',
    action: '操作', time: '日時', route: '拠点', actor: '記録者', event: 'イベント', entity: '記録', details: '詳細', readOnly: '入出庫や補充申請には作業者権限へ切り替えてください。', managerHint: '申請を承認・却下するには管理者権限へ切り替えてください。',
    connection: 'APIに接続できません。バックエンドを起動して再試行してください。', loading: '倉庫データを読み込み中…', footer: 'Budi Juarto 制作 · React / TypeScript / FastAPI / SQLite',
    insufficient_stock: '移動元の在庫が不足しています。データは変更されていません。', idempotency_conflict: '同じキーで異なるデータが使用されました。画面を閉じて新しい処理を作成してください。', invalid_locations: '有効で異なる移動元・移動先を選択してください。', unknown_location: '拠点が見つかりません。', unknown_product: '商品が見つかりません。', read_only: 'この権限では在庫を変更できません。', manager_required: '管理者による判断が必要です。', approval_required: '入庫前に補充申請を承認してください。', request_state_conflict: '申請の状態は変更されています。更新して現在の状態を確認してください。', database_unavailable: 'データベース処理を完了できませんでした。同じ操作を再試行してください。', invalidInput: '数量・拠点・参照番号を確認してください。数量は正の整数にしてください。', failed: '操作を完了できませんでした。再試行してください。',
  },
} as const;

const sectionIcons = { overview: LayoutDashboard, inventory: Package, movements: ArrowRightLeft, requests: ClipboardCheck, audit: ShieldCheck };
const movementIcons = { receive: ArrowDownLeft, issue: ArrowUpRight, transfer: ArrowRightLeft };

export default function App() {
  const [lang, setLang] = useState<Language>('en');
  const [role, setRole] = useState<Role>('operator');
  const [section, setSection] = useState<Section>('overview');
  const [data, setData] = useState<State | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [query, setQuery] = useState('');
  const [lowOnly, setLowOnly] = useState(false);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [kind, setKind] = useState<Kind>('receive');
  const [productId, setProductId] = useState(1);
  const [quantity, setQuantity] = useState('10');
  const [source, setSource] = useState('A');
  const [destination, setDestination] = useState('B');
  const [reference, setReference] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState('');
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  const receiptKeys = useRef(new Map<string, string>());
  const t = copy[lang];

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/state', { headers: { 'X-Demo-Role': role } });
      if (!response.ok) throw new Error('connection');
      setData(await response.json() as State);
    } catch { setError('connection'); }
    finally { setLoading(false); }
  }, [role]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  useEffect(() => {
    if (!dialog) return;
    const handleKey = (event: KeyboardEvent) => { if (event.key === 'Escape' && !busy) setDialog(null); };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [dialog, busy]);

  const errorText = (code: string) => t[code as keyof typeof t] ?? t.failed;
  const productName = (id: number) => { const p = data?.products.find(p => p.id === id); return p ? `${p.sku} · ${lang === 'ja' ? p.name_ja : p.name_en}` : String(id); };
  const time = (value: string) => new Intl.DateTimeFormat(lang === 'ja' ? 'ja-JP' : 'en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
  const visibleProducts = useMemo(() => data?.products.filter(p => (!lowOnly || p.low_stock) && `${p.sku} ${p.name_en} ${p.name_ja}`.toLowerCase().includes(query.toLowerCase())) ?? [], [data, query, lowOnly]);
  const openDialog = (next: Dialog, id = 1) => {
    setDialog(next); setProductId(id); setFormError(''); setReference(''); setNote(''); setQuantity('10'); retry.current = null;
  };
  async function post(path: string, body: unknown) {
    let response: Response;
    try { response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Demo-Role': role }, body: JSON.stringify(body) }); }
    catch { throw new Error('connection'); }
    const result = await response.json();
    if (!response.ok) throw new Error(result.error?.code ?? (response.status === 422 ? 'invalidInput' : 'failed'));
    return result;
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setFormError('');
    const count = Number(quantity);
    if (!Number.isInteger(count) || count <= 0 || count > 100000) { setFormError('invalidInput'); return; }
    setBusy(true);
    try {
      let result;
      if (dialog === 'movement') {
        const body = { kind, product_id: productId, quantity: count, from_location: kind === 'receive' ? null : source, to_location: kind === 'issue' ? null : destination, reference: reference.trim() };
        const fingerprint = JSON.stringify(body);
        if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
        result = await post('/api/movements', { ...body, idempotency_key: retry.current.key });
      } else {
        result = await post('/api/requests', { product_id: productId, quantity: count, location: destination, note: note.trim() });
      }
      setNotice(result.replayed ? 'replayed' : 'success'); setDialog(null); await load();
    } catch (reason) { setFormError(reason instanceof Error ? reason.message : 'failed'); }
    finally { setBusy(false); }
  }
  async function act(request: StockRequest, action: 'approve' | 'reject' | 'receive') {
    setBusy(true); setError(''); setNotice('');
    try {
      if (action === 'receive') {
        if (!receiptKeys.current.has(request.id)) receiptKeys.current.set(request.id, crypto.randomUUID());
        const result = await post(`/api/requests/${request.id}/receive`, { idempotency_key: receiptKeys.current.get(request.id) });
        setNotice(result.replayed ? 'replayed' : 'success');
      } else {
        await post(`/api/requests/${request.id}/decision`, { decision: action }); setNotice('success');
      }
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'failed'); }
    finally { setBusy(false); }
  }
  async function exportCSV() {
    try {
      const response = await fetch('/api/inventory.csv', { headers: { 'X-Demo-Role': role } });
      if (!response.ok) throw new Error();
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'warehouse-inventory.csv'; anchor.click(); URL.revokeObjectURL(url);
    } catch { setError('connection'); }
  }
  const movementTable = (rows: StockMovement[]) => <div className="table-wrap"><table><thead><tr><th>{t.time}</th><th>{t.movementType}</th><th>{t.product}</th><th>{t.quantity}</th><th>{t.route}</th><th>{t.reference}</th><th>{t.actor}</th></tr></thead><tbody>{rows.map(row => {
    const Icon = movementIcons[row.kind];
    return <tr key={row.id}><td className="muted nowrap">{time(row.created_at)}</td><td><span className={`movement-kind ${row.kind}`}><Icon size={14}/>{t[row.kind]}</span></td><td>{productName(row.product_id)}</td><td className="numeric">{row.quantity}</td><td className="mono">{row.from_location ?? '—'} → {row.to_location ?? '—'}</td><td className="mono small">{row.reference}</td><td className="muted small">{row.actor}</td></tr>;
  })}</tbody></table>{rows.length === 0 && <p className="empty">{t.noResults}</p>}</div>;

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#" onClick={event => { event.preventDefault(); setSection('overview'); }}><span className="brand-icon"><Layers3 size={24}/></span><span>warehouse<span className="brand-suffix"> / DX</span></span></a>
      <p className="brand-note">{t.tagline}</p><span className="nav-label">{t.workspace}</span>
      <nav aria-label={t.workspace}>{(Object.keys(sectionIcons) as Section[]).map(item => { const Icon = sectionIcons[item]; return <button key={item} className={`nav-item ${section === item ? 'selected' : ''}`} aria-current={section === item ? 'page' : undefined} onClick={() => setSection(item)}><Icon size={18}/>{t[item]}{item === 'requests' && !!data?.summary.pending_requests && <span className="nav-count">{data.summary.pending_requests}</span>}</button>; })}</nav>
      <div className="sidebar-bottom"><span className="live-dot"/> {t.demo}<p>{t.demoNote}</p><div className="author">BUDI JUARTO <ArrowUpRight size={15}/></div></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="breadcrumb"><span>{t.pageTitle}</span><ChevronRight size={13}/><strong>{t[section]}</strong></div><div className="top-controls"><button className="language" aria-label="Switch language" onClick={() => setLang(lang === 'en' ? 'ja' : 'en')}><Globe2 size={16}/>{lang === 'en' ? '日本語' : 'English'}</button><label className="sr-only" htmlFor="role">Demo role</label><select id="role" value={role} disabled={busy} onChange={event => setRole(event.target.value as Role)}>{(['viewer', 'operator', 'manager'] as Role[]).map(r => <option key={r} value={r}>{t[r]}</option>)}</select><span className="avatar">BJ</span></div></header>
      <main>
        <div className="page-heading"><div><div className="eyebrow">OPERATIONS / 01</div><h1>{section === 'overview' ? t.pageTitle : t[section]}</h1><p>{t.pageSubtitle}</p></div><div className="heading-actions"><button className="button subtle" disabled={loading || busy} onClick={() => void load()}><RefreshCw size={16} className={loading ? 'spin' : ''}/>{t.refresh}</button><button className="button primary" disabled={role === 'viewer' || busy || !data} onClick={() => openDialog(section === 'requests' ? 'request' : 'movement')}><Plus size={17}/>{section === 'requests' ? t.addRequest : t.addMovement}</button></div></div>
        {error && <div className="banner error" role="alert"><span>{errorText(error)}</span><button onClick={() => void load()}>{t.refresh}</button></div>}
        {notice && <div className="banner success" role="status"><Check size={17}/><span>{errorText(notice)}</span><button aria-label="Dismiss" onClick={() => setNotice('')}><X size={16}/></button></div>}
        {role === 'viewer' && <p className="role-hint"><ShieldCheck size={15}/>{t.readOnly}</p>}
        {!data ? <div className="loading-state"><LoaderCircle className="spin" size={30}/><p>{error ? t.connection : t.loading}</p></div> : <>
          {section === 'overview' && <>
            <div className="metrics">{[{ label: t.active, value: data.summary.active_skus, Icon: Package, tag: 'SKU' }, { label: t.low, value: data.summary.low_stock, Icon: Activity, tag: 'ALERT', warning: true }, { label: t.pending, value: data.summary.pending_requests, Icon: ClipboardCheck, tag: 'WORKFLOW' }, { label: t.totalMovements, value: data.summary.movement_count, Icon: ArrowRightLeft, tag: 'LOGGED' }].map(({ label, value, Icon, tag, warning }) => <article className={`metric ${warning ? 'warning' : ''}`} key={label}><div className="metric-top"><span>{label}</span><Icon size={18}/></div><div className="metric-value">{value.toLocaleString()}<span>{tag}</span></div><div className="metric-line"/></article>)}</div>
            <div className="overview-grid"><section className="card distribution"><div className="card-heading"><div><h2>{t.distribution}</h2><p>{t.distributionNote}</p></div><span className="icon-box"><Truck size={19}/></span></div><div className="chart-legend"><span><i className="legend-main"/>{t.main}</span><span><i className="legend-dispatch"/>{t.dispatch}</span></div>{data.products.map(p => <div className="stock-chart-row" key={p.id}><div><strong>{lang === 'ja' ? p.name_ja : p.name_en}</strong><span className="mono">{p.sku}</span></div><div className="stock-bar" aria-label={`${p.sku}: A ${p.balances.A ?? 0}, B ${p.balances.B ?? 0}`}><span style={{ width: `${(p.balances.A ?? 0) / Math.max(1, p.total) * 100}%` }}/><span style={{ width: `${(p.balances.B ?? 0) / Math.max(1, p.total) * 100}%` }}/></div><div className="stock-chart-total">{p.total}<small>{p.unit}</small></div></div>)}</section><section className="card attention"><div className="card-heading"><div><h2>{t.attention}</h2><p>{t.attentionNote}</p></div><span className="attention-number">{data.summary.low_stock}</span></div>{data.products.filter(p => p.low_stock).map(p => <article className="attention-item" key={p.id}><div className="item-icon"><Package size={18}/></div><div><strong>{lang === 'ja' ? p.name_ja : p.name_en}</strong><span>{p.total} / {p.reorder_point} {p.unit}</span></div><button disabled={role === 'viewer' || busy} aria-label={`${t.addRequest}: ${p.sku}`} onClick={() => openDialog('request', p.id)}><Plus size={18}/></button></article>)}{data.summary.low_stock === 0 && <p className="empty">{t.noResults}</p>}<div className="workflow-note"><ShieldCheck size={18}/><p>{t.requestNote}</p></div></section></div>
            <section className="card"><div className="card-heading"><h2>{t.recent}</h2><button className="text-button" onClick={() => setSection('movements')}>{t.viewAll}<ChevronRight size={15}/></button></div>{movementTable(data.movements.slice(0, 5))}</section>
          </>}
          {section === 'inventory' && <section className="card"><div className="inventory-toolbar"><label className="search"><Search size={17}/><input aria-label={t.search} placeholder={t.search} value={query} onChange={event => setQuery(event.target.value)}/></label><div className="toolbar-end"><select aria-label="Stock filter" value={lowOnly ? 'low' : 'all'} onChange={event => setLowOnly(event.target.value === 'low')}><option value="all">{t.allStock}</option><option value="low">{t.lowOnly}</option></select><button className="button subtle" onClick={() => void exportCSV()}><Download size={16}/>{t.export}</button></div></div><div className="table-wrap"><table><thead><tr><th>{t.sku}</th><th>{t.main} / A</th><th>{t.dispatch} / B</th><th>{t.total}</th><th>{t.reorder}</th><th>{t.status}</th><th>{t.action}</th></tr></thead><tbody>{visibleProducts.map(p => <tr key={p.id}><td><div className="product-cell"><span className="product-icon"><Package size={19}/></span><span><strong>{lang === 'ja' ? p.name_ja : p.name_en}</strong><small className="mono">{p.sku} · {p.unit}</small></span></div></td><td className="numeric">{p.balances.A ?? 0}</td><td className="numeric">{p.balances.B ?? 0}</td><td className="numeric strong">{p.total}</td><td className="numeric muted">{p.reorder_point}</td><td><span className={`badge ${p.low_stock ? 'low' : 'healthy'}`}><i/>{p.low_stock ? t.lowBadge : t.healthy}</span></td><td><button className="text-button" disabled={role === 'viewer' || busy} onClick={() => openDialog('movement', p.id)}>{t.addMovement}<ChevronRight size={14}/></button></td></tr>)}</tbody></table>{visibleProducts.length === 0 && <p className="empty">{t.noResults}</p>}</div></section>}
          {section === 'movements' && <section className="card"><div className="card-heading"><h2>{t.movements}</h2><span className="muted small">{data.movements.length} / {data.summary.movement_count}</span></div>{movementTable(data.movements)}</section>}
          {section === 'requests' && <section className="card"><div className="card-heading"><h2>{t.requests}</h2><p>{t.managerHint}</p></div><div className="request-list">{data.requests.map(request => <article className="request-card" key={request.id}><div className="request-title"><div><span className="mono muted small">{request.id}</span><h3>{productName(request.product_id)}</h3></div><span className={`badge ${request.status}`}>{t[request.status]}</span></div><p>{request.note}</p><div className="request-meta"><span>{t.quantity}: <strong>{request.quantity}</strong></span><span>{t.location}: <strong>{request.location}</strong></span><span>{time(request.created_at)}</span></div><div className="request-actions">{request.status === 'open' && role === 'manager' && <><button className="button subtle" disabled={busy} onClick={() => void act(request, 'reject')}>{t.reject}</button><button className="button primary" disabled={busy} onClick={() => void act(request, 'approve')}><Check size={16}/>{t.approval}</button></>}{request.status === 'approved' && role !== 'viewer' && <button className="button primary" disabled={busy} onClick={() => void act(request, 'receive')}><ArrowDownLeft size={16}/>{t.receiveApproved}</button>}</div></article>)}{data.requests.length === 0 && <p className="empty">{t.noResults}</p>}</div></section>}
          {section === 'audit' && <section className="card"><div className="card-heading"><div><h2>{t.audit}</h2><p>{t.saveNote}</p></div><ShieldCheck size={20}/></div><div className="table-wrap"><table><thead><tr><th>{t.time}</th><th>{t.event}</th><th>{t.entity}</th><th>{t.actor}</th><th>{t.details}</th></tr></thead><tbody>{data.audit.map(item => <tr key={item.id}><td className="nowrap muted">{time(item.created_at)}</td><td><span className="audit-event">{item.event}</span></td><td className="mono small">{item.entity_id}</td><td className="small">{item.actor}</td><td><code className="audit-detail">{item.detail}</code></td></tr>)}</tbody></table></div></section>}
          <footer><span>{t.footer}</span><span className="updated"><i/>{t.updated}: {time(data.generated_at)}</span></footer>
        </>}
      </main>
    </div>
    {dialog && data && <div className="dialog-backdrop" onClick={event => { if (event.target === event.currentTarget && !busy) setDialog(null); }}><section className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title"><div className="dialog-heading"><div><span className="eyebrow">WAREHOUSE / WORKFLOW</span><h2 id="dialog-title">{dialog === 'movement' ? t.addMovement : t.addRequest}</h2></div><button className="icon-button" aria-label={t.cancel} disabled={busy} onClick={() => setDialog(null)}><X size={20}/></button></div><form onSubmit={event => void save(event)}><fieldset disabled={busy}><label>{t.product}<select value={productId} autoFocus onChange={event => setProductId(Number(event.target.value))}>{data.products.map(p => <option key={p.id} value={p.id}>{productName(p.id)}</option>)}</select></label>{dialog === 'movement' && <label>{t.movementType}<div className="segmented">{(['receive', 'issue', 'transfer'] as Kind[]).map(item => <button type="button" className={kind === item ? 'active' : ''} key={item} onClick={() => setKind(item)}>{t[item]}</button>)}</div></label>}<div className="form-row"><label>{t.quantity}<input type="number" min="1" max="100000" step="1" required value={quantity} onChange={event => setQuantity(event.target.value)}/></label>{(dialog === 'request' || kind !== 'issue') && <label>{dialog === 'request' ? t.location : t.destination}<select value={destination} onChange={event => setDestination(event.target.value)}>{data.locations.map(l => <option key={l.id} value={l.id}>{l.id} · {lang === 'ja' ? l.name_ja : l.name_en}</option>)}</select></label>}</div>{dialog === 'movement' && kind !== 'receive' && <label>{t.source}<select value={source} onChange={event => setSource(event.target.value)}>{data.locations.map(l => <option key={l.id} value={l.id}>{l.id} · {lang === 'ja' ? l.name_ja : l.name_en} ({data.products.find(p => p.id === productId)?.balances[l.id] ?? 0})</option>)}</select></label>}{dialog === 'movement' ? <label>{t.reference}<input required minLength={3} maxLength={100} value={reference} placeholder="PO-DEMO-001" onChange={event => setReference(event.target.value)}/></label> : <label>{t.note}<textarea required minLength={3} maxLength={200} rows={3} value={note} onChange={event => setNote(event.target.value)}/></label>}<p className="form-note"><ShieldCheck size={16}/>{dialog === 'movement' ? t.saveNote : t.requestNote}</p></fieldset>{formError && <div className="banner error" role="alert">{errorText(formError)}</div>}<div className="dialog-actions"><button className="button subtle" type="button" disabled={busy} onClick={() => setDialog(null)}>{t.cancel}</button><button className="button primary" type="submit" disabled={busy}>{busy ? <LoaderCircle className="spin" size={16}/> : <Check size={16}/>}{dialog === 'movement' ? t.save : t.createRequest}</button></div></form></section></div>}
  </div>;
}
