import { useState } from "react";
import "./index.css";
import brandHero from "./assets/brand.jpg";       // main image (you already fixed)
import fallbackLogo from "./assets/guzo-logo.svg"; // fallback if brand.jpg fails

/* ---------- Reusable image with fallback + skeleton + fade ---------- */
function ImageWithFallback({ src, alt, className = "", ratio = "16/10" }) {
  const [loaded, setLoaded] = useState(false);
  const [err, setErr] = useState(false);

  const finalSrc = err ? fallbackLogo : src;

  return (
    <div className={`img-wrap ${loaded ? "is-loaded" : ""}`} style={{ aspectRatio: ratio }}>
      {!loaded && <div className="img-skeleton" aria-hidden="true" />}
      <img
        src={finalSrc}
        alt={alt}
        onLoad={() => setLoaded(true)}
        onError={() => setErr(true)}
        className={`fade-in ${className}`}
        loading="lazy"
        decoding="async"
      />
    </div>
  );
}

/* ---------- Small, reusable card ---------- */
function Card({ children, padded = true }) {
  return <div className="card" style={{ padding: padded ? 20 : 0 }}>{children}</div>;
}

export default function GuzoLandingPage() {
  const [lang, setLang] = useState("en");
  const [form, setForm] = useState({ name: "", email: "", message: "" });
  const [sent, setSent] = useState(false);

  const t = (en, am, om) => (lang === "am" ? am : lang === "om" ? om : en);

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: hook this to your Python backend (SendGrid + Google Sheet)
    console.log("Demo Request:", form);
    setSent(true);
    setTimeout(() => setSent(false), 4000);
    setForm({ name: "", email: "", message: "" });
  };

  return (
    <div>
      {/* ========================= HEADER ========================= */}
      <header className="header" aria-label="Site header">
        <div className="container header__wrap">
          <a href="#" className="header__brand" aria-label="Guzo Guest Assist home">
            <span className="brand-avatar" aria-hidden="true">
              <ImageWithFallback src={brandHero} alt="Guzo Guest Assist logo" ratio="1/1" className="brand-avatar__img" />
              <span className="brand-ring"></span>
            </span>
            <span>Guzo Guest Assist</span>
          </a>

          <nav className="header__lang" aria-label="Language switcher">
            {[
              { id: "en", label: "EN" },
              { id: "am", label: "አማ" },
              { id: "om", label: "Om" },
            ].map((opt) => (
              <button
                key={opt.id}
                onClick={() => setLang(opt.id)}
                className={`lang-btn ${lang === opt.id ? "lang-btn--active" : ""}`}
                aria-pressed={lang === opt.id}
              >
                {opt.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main>
        {/* ========================= HERO ========================= */}
        <section className="section" id="home">
          <div className="container split">
            <div>
              <h1 className="h1" style={{ marginTop: 16 }}>
                {t(
                  "AI Concierge & Booking for Ethiopian Hospitality",
                  "ለኢትዮጵያ አቅጣጫ የተሟላ የAI ኮንሰርጅ እና ቦኪንግ",
                  "AI Concierge fi Booking tajaajila hotelii Itiyoophiyaa"
                )}
              </h1>
              <p className="muted" style={{ marginTop: 12 }}>
                {t(
                  "Trilingual service (EN/Amharic/Afan Oromo), instant bookings, Google Sheets analytics, and auto email receipts.",
                  "ትሪላንጉዋል አገልግሎት (እንግ/አማ/ኦሮ)፣ ፈጣን ቦኪንግ፣ የGoogle Sheets ትንተና፣ እና በኢሜይል የሚላኩ ደረሰኞች።",
                  "Tajaajila afaan sadii, booking saffisaa, Google Sheets falmisiisuu fi emailiin ragaa ergu."
                )}
              </p>

              <div className="hero__chips" style={{ marginTop: 14 }}>
                <span className="chip">EN / አማ / Om</span>
                <span className="chip">Telegram & WhatsApp</span>
                <span className="chip">Google Sheets</span>
                <span className="chip">Auto Confirmations</span>
              </div>

              <div style={{ display: "flex", gap: 12, marginTop: 22, flexWrap: "wrap" }}>
                <a href="https://t.me/your_bot_username" target="_blank" rel="noreferrer" className="btn btn--ink">
                  {t("Try Telegram Demo", "በቴሌግራም ተሞክር", "Telegram irratti qabadhu")}
                </a>
                <a href="#demo" className="btn btn--outline">
                  {t("Request a Demo", "ዴሞ ጠይቅ", "Demo gaafadhu")}
                </a>
              </div>
            </div>

            <Card padded={false}>
              <ImageWithFallback src={brandHero} alt="Guzo showcase" ratio="16/10" />
            </Card>
          </div>
        </section>

        {/* ========================= VALUE PROPS ========================= */}
        <section className="section" id="value">
          <div className="container">
            <div className="grid-cards">
              <Card><b>{t("Increase Direct Bookings", "ቀጥታ ቦኪንግ አበርክት", "Booking kallattii dura dabali")}</b><br/>
                <span className="muted">{t("Convert chats into confirmed stays in minutes.", "ውይይቶችን በደቂቃዎች ውስጥ ወደ ተረጋገጠ ቆይታ አስቀምጥ።","Waliigaltee xumuru saffisiisi.")}</span>
              </Card>
              <Card><b>{t("Operate in 3 Languages", "በ3 ቋንቋ ተግባር", "Afaan sadii hojiirra oolchi")}</b><br/>
                <span className="muted">{t("EN/Amharic/Afan Oromo, hospitality tone built-in.", "እንግ/አማ/ኦሮ በሙያዊ ቋንቋ ስርዓት።","EN/Amh/AO af-gaaddisa tajaajila hoteela.")}</span>
              </Card>
              <Card><b>{t("No PMS Required", "PMS አያስፈልግም", "PMS hin barbaachisu")}</b><br/>
                <span className="muted">{t("Start with Google Sheets; connect PMS later.", "በGoogle Sheets ጀምር፣ PMS በኋላ አገናኝ።","Google Sheets irraa jalqabi; booda PMS walitti hidhi.")}</span>
              </Card>
              <Card><b>{t("Automated Emails & Receipts", "ራስ-ሰር ኢሜይሎች እና ደረሰኞች", "Imeelii fi ragaa ofumaan ergu")}</b><br/>
                <span className="muted">{t("Instant confirmations via SendGrid.", "በSendGrid ወዲያውኑ ማረጋገጫ።","Mirkaneessa saffisaa SendGrid'n.")}</span>
              </Card>
            </div>
          </div>
        </section>

        {/* ========================= HOW IT WORKS ========================= */}
        <section className="section" id="how">
          <div className="container">
            <h2 className="h2" style={{ marginBottom: 16 }}>{t("How it works", "እንዴት ይሰራ?", "Akka hojjatu")}</h2>
            <div className="grid-steps">
              {[
                { n: "01", en: "Guest messages your Telegram/WhatsApp.", am: "እንግዳው በቴሌግራም/ዋትስአፕ መልዕክት ይልካል።", om: "Daawwataan Telegram/WhatsApp si qunname." },
                { n: "02", en: "Bot collects stay dates, room type, name & email.", am: "ቦቱ ቀናት፣ ክፍል፣ ስም እና ኢሜል ይሰብስባል።", om: "Guyyaa, kutaa, maqaa, email funaana." },
                { n: "03", en: "Booking auto-logs to Google Sheets & dashboard.", am: "ቦኪንግ በራስ-ሰር ወደ Google Sheets እና ዳሽቦርድ ይመዘገባል።", om: "Google Sheets fi dashboarditti galmaa'a." },
                { n: "04", en: "Confirmation & receipt sent by email.", am: "ማረጋገጫ እና ደረሰኝ በኢሜል ይላካሉ።", om: "Mirkaneessi fi ragaan emailiin ergame." },
              ].map((s) => (
                <div className="step" key={s.n}>
                  <div className="step__num">{s.n}</div>
                  <div style={{ fontWeight: 700, marginTop: 6 }}>{t(s.en, s.am, s.om)}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ========================= FEATURES ========================= */}
        <section className="section" id="features">
          <div className="container">
            <h2 className="h2" style={{ marginBottom: 16 }}>{t("Key features", "ዋና ጥቅሞች", "Amaloota ijoo")}</h2>
            <div className="grid-cards">
              <Card><b>{t("Tri-lingual Chat", "ትሪላንጉዋል ውይይት", "Waltajjii afaan sadii")}</b><br/><span className="muted">{t("English / Amharic / Afan Oromo with hospitality tone.","እንግ/አማ/ኦሮ በሙያዊ ቅኔ።","EN/Amh/AO afaan tajaajila hoteela.")}</span></Card>
              <Card><b>{t("Google Sheets Sync", "ወደ Google Sheets መዋል", "Google Sheets waliin walsimsiisi")}</b><br/><span className="muted">{t("Property sheet + Central dashboard.","የንብረት ሺት + ማእከላዊ ዳሽቦርድ።","Sheet qabeenyaa + dashboard giddugalaa.")}</span></Card>
              <Card><b>{t("Auto Emails & Receipts", "ራስ-ሰር ኢሜይል እና ደረሰኝ", "Imeelii fi ragaa ofumaan")}</b><br/><span className="muted">{t("SendGrid confirmations out-of-the-box.","SendGrid ማረጋገጫ ዝግጁ ነው።","SendGrid mirkaneessa qopheessa.")}</span></Card>
              <Card><b>{t("Availability Ready", "ክፍትነት ዝግጁ", "Argamuu qopheessa")}</b><br/><span className="muted">{t("Start with Sheets; connect PMS/Channel Manager later.","በSheets ጀምር፣ PMS/Channel በኋላ አገናኝ።","Sheets jalqabi; boodarra PMS/Channel.")}</span></Card>
              <Card><b>{t("Manager Routing", "ወደ ማኔጀር መዘዋወር", "Garee bulchaa geessi")}</b><br/><span className="muted">{t("Escalate to staff at any step.","በማንኛውም ደረጃ ወደ ሰራተኞች አስተላልፍ።","Hanga fedhetti hojjettootaatti dabarsi.")}</span></Card>
              <Card><b>{t("Analytics", "ትንተና", "Falmiinsa")}</b><br/><span className="muted">{t("Occupancy, ADR, RevPAR, revenue summaries.","Occupancy, ADR, RevPAR እና ገቢ ማጠቃለያዎች።","Ittigaafatamummaa, ADR, RevPAR, gabaasa.")}</span></Card>
            </div>
          </div>
        </section>

        {/* ========================= ANALYTICS PREVIEW ========================= */}
        <section className="section" id="analytics">
          <div className="container">
            <Card>
              <h2 className="h2" style={{ marginBottom: 12 }}>{t("Analytics preview", "የትንተና እይታ", "Ilaalcha falmisiisuu")}</h2>
              <div className="kpi-row">
                <div className="kpi"><div className="kpi__value">78%</div><div className="muted">Occupancy</div></div>
                <div className="kpi"><div className="kpi__value">ETB 3,600</div><div className="muted">ADR</div></div>
                <div className="kpi"><div className="kpi__value">ETB 2,800</div><div className="muted">RevPAR</div></div>
                <div className="kpi"><div className="kpi__value">ETB 1.2M</div><div className="muted">Revenue (30d)</div></div>
              </div>
              <p className="muted" style={{ marginTop: 12 }}>
                {t("Get weekly emails summarizing trends and performance.",
                   "የሳምንት ኢሜይሎች የአፈፃፀም እና ዝንባሌ ማጠቃለያ ይላካሉ።",
                   "Email torbaanii gabaasa ammayyaa siif erga.")}
              </p>
            </Card>
          </div>
        </section>

        {/* ========================= INTEGRATIONS ========================= */}
        <section className="section" id="integrations">
          <div className="container">
            <h2 className="h2" style={{ marginBottom: 12 }}>{t("Integrations", "ኢንተግሬሽኖች", "Walitti hidhamoota")}</h2>
            <div className="logos-row">
              <span className="logo-pill">Telegram</span>
              <span className="logo-pill">WhatsApp (soon)</span>
              <span className="logo-pill">Google Sheets</span>
              <span className="logo-pill">SendGrid</span>
              <span className="logo-pill">PMS (optional)</span>
            </div>
          </div>
        </section>

        {/* ========================= PRICING ========================= */}
        <section className="section" id="pricing">
          <div className="container">
            <h2 className="h2" style={{ marginBottom: 16 }}>{t("Simple pricing", "ቀላል ዋጋ", "Gatii salphaa")}</h2>
            <div className="grid-cards">
              <Card>
                <div style={{ fontWeight: 800, fontSize: 18, marginBottom: 6 }}>{t("Starter (Pilot)", "ጀማሪ (ፓይሎት)", "Starter (Pilot)")}</div>
                <div className="muted">{t("Free setup, up to X bookings/month, basic support.", "ነጻ ማቀናበር፣ እስከ X ቦኪንግ/ወር፣ መሰረታዊ ድጋፍ።","Qopheessa bilisa; X booking/ji'a; tajaajila bu'uura.")}</div>
              </Card>
              <Card>
                <div style={{ fontWeight: 800, fontSize: 18, marginBottom: 6 }}>{t("Pro (Per Property)", "ፕሮ (በንብረት)", "Pro (Qabeenya)")}</div>
                <div className="muted">{t("Flat monthly fee, priority support, analytics reports.", "የወር ቋሚ ክፍያ፣ ቅድሚያ ድጋፍ፣ የትንተና ሪፖርቶች።","Kaffaltii ji'aan; deeggarsa dursa; gabaasa falmisiisuu.")}</div>
              </Card>
            </div>
            <p className="muted" style={{ marginTop: 10 }}>
              {t("Contact us for early-partner discounts.", "ለቀድሞ ባለትዳር ቅናሽ ያግኙን።", "Gatii hir'isu haala qindeessuuf nu qunnamii.")}
            </p>
          </div>
        </section>

        {/* ========================= FAQ ========================= */}
        <section className="section" id="faq">
          <div className="container">
            <h2 className="h2" style={{ marginBottom: 14 }}>FAQ</h2>
            <div className="faq">
              {[
                {
                  q: t("Do I need a PMS?", "PMS ያስፈልጋል?", "PMS barbaachisaa?"),
                  a: t("No. Start with Google Sheets; connect PMS later.", "አይፈልግም። በGoogle Sheets ጀምር፣ PMS በኋላ አገናኝ።", "Hin barbaachisu; Google Sheets irraa jalqabi; boodarra PMS walitti hidhi.")
                },
                {
                  q: t("Can staff intervene mid-chat?", "ሰራተኛ መካከል ሊገባ ይችላል?", "Hojjetaan keessa seenuu ni danda'aa?"),
                  a: t("Yes. You can escalate to a manager at any step.", "አዎን። በማንኛውም ደረጃ ወደ ማኔጀር ማስተላለፍ ይቻላል።", "Eeyyee; mataduree bulchaa geessuu ni dandeessa.")
                },
                {
                  q: t("Which languages are supported?", "ምን ቋንቋዎች ይደገፋሉ?", "Afaan kamtu ni deeggarama?"),
                  a: t("English, Amharic, and Afan Oromo.", "እንግሊዝኛ፣ አማርኛ፣ አፋን ኦሮሞ።", "Afaan Ingiliffaa, Amaariffaa fi Afaan Oromoo.")
                },
                {
                  q: t("How do confirmations work?", "ማረጋገጫዎች እንዴት ይሰራሉ?", "Mirkaneessoonni akkamiin hojjetu?"),
                  a: t("Auto emails via SendGrid with booking summary.", "በSendGrid በራስ-ሰር ኢሜይል ከቦኪንግ ማጠቃለያ ጋር።", "Imeelii SendGrid'n ofumaan, gabaasa waliin.")
                },
                {
                  q: t("Can I export my data?", "ውሂቴን ማውጣት እችላለሁ?", "Daataa koo baasuu nan danda'aa?"),
                  a: t("Yes—CSV from Google Sheets anytime.", "አዎን—CSV ከGoogle Sheets በማንኛውም ጊዜ።", "Eeyyee—CSV Google Sheets irraa yoom iyyuu.")
                }
              ].map((f, i) => (
                <div className="faq__item" key={i}>
                  <div className="faq__q">{f.q}</div>
                  <div className="faq__a muted">{f.a}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ========================= DEMO / CONTACT ========================= */}
        <section className="section" id="demo">
          <div className="container">
            <Card>
              <h2 className="h2" style={{ marginBottom: 8 }}>
                {t("Request a live demo", "የቀጥታ ዴሞ ጠይቅ", "Demo jiraataa gaafadhu")}
              </h2>
              <p className="muted" style={{ marginBottom: 16 }}>
                {t(
                  "Tell us your property name and preferred contact. We’ll follow up with a calendar link.",
                  "የንብረት ስም እና የመገናኛ መንገድ ይንገሩን። በቀጣይ የቆጠብ አገናኝ እናስቀምጣለን።",
                  "Maqaa qabeenyaa fi qunnamtii filatamuu nuu himi; linkii kallandaraa ni erga."
                )}
              </p>

              <form className="form" onSubmit={handleSubmit}>
                <input className="input" type="text" placeholder={t("Your name", "ስምዎ", "Maqaa kee")}
                  value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required aria-label={t("Your name", "ስምዎ", "Maqaa kee")} />

                <input className="input" type="email" placeholder={t("Work email", "የስራ ኢሜይል", "Imeelii hojii")}
                  value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required aria-label={t("Work email", "የስራ ኢሜይል", "Imeelii hojii")} />

                <textarea className="textarea" placeholder={t(
                  "Property name, city, and what you want to test.",
                  "የንብረት ስም፣ ከተማ እና ምን መሞከር እፈልጋለሁ።",
                  "Maqaa qabeenyaa, magaalaa, wanta qorachu barbaaddu."
                )}
                  value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })}
                  aria-label={t("Message", "መልእክት", "Ergaa")} />

                <button type="submit" className="btn btn--ink form__submit">
                  {t("Send request", "ጥያቄ ላክ", "Gaaffii ergi")}
                </button>

                {sent && (
                  <div className="muted" role="status" aria-live="polite" style={{ marginTop: 6 }}>
                    {t("Thanks! We'll contact you soon.","አመሰግናለሁ! በቅርቡ እናገናኝዎታለን።","Galatoomi! Akkuma boodatti si qunnamna.")}
                  </div>
                )}
              </form>
            </Card>
          </div>
        </section>
      </main>

      {/* ========================= FOOTER ========================= */}
      <footer className="footer">
        <div className="container footer__wrap">
          <div>© {new Date().getFullYear()} Guzo Guest Assist</div>
          <nav className="footer__links" aria-label="Footer links">
            <a className="footer__link" href="#how">{t("How it works", "እንዴት ይሰራ?", "Akka hojjatu")}</a>
            <a className="footer__link" href="#demo">{t("Request demo", "ዴሞ ጠይቅ", "Demo gaafadhu")}</a>
            <a className="footer__link" href="mailto:no-reply@guzoassist.com">no-reply@guzoassist.com</a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
