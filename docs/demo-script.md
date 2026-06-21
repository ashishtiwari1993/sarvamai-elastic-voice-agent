# 🎬 Pratham Bank · Mitr — Demo Recording Script (Role-Play)

A screenplay for recording the voice demo. **You play the CALLER** — read only the
**Caller** lines aloud. **Mitr is the app** — it answers on its own; the *Mitr* lines
below are the *expected* gist (the live wording will vary slightly).

Everything here matches the seeded data (names, DOBs, amounts, payees, dates).

### How to drive the app while recording
1. Pick the caller card at the top, then click **↻ New call** (this re-arms identity verification).
2. Before each line, click the **language chip** shown in `[brackets]` (or leave on **Auto**).
3. Tap the **mic**, speak the Caller line, tap again to stop. Wait for Mitr to reply (audio + text).
4. To start a different scene, switch the caller card and click **↻ New call**.

> Tip: run the browser on `http://localhost:8000` so the mic works. For each Hindi/Marathi
> line, the Devanagari is what to say; the *(roman)* and *(English)* are just for you.

---

## 🎯 SCENE 1 — Priya Sharma · UPI fraud · switches English → Hindi → Marathi → English
**Caller card:** Priya Sharma (Pune) · **DOB for verification:** 2 November 1995

**Turn 1 — `[English]`**
- **Caller:** "Hello, I think some money has gone out of my account that I never authorised."
- **Mitr (expected, English):** "I can help with that. For your security, please tell me your date of birth to verify your identity."

**Turn 2 — `[हिंदी]`** *(give DOB + describe the problem, in Hindi)*
- **Caller (Hindi):** "मेरी जन्मतिथि दो नवंबर उन्नीस सौ पचानवे है। मेरे खाते से पैसे कट गए हैं, मैंने कोई पेमेंट नहीं किया।"
  - *(roman)* "Meri janm-tithi do November unnees-sau-pachaanave hai. Mere khaate se paise kat gaye hain, maine koi payment nahi kiya."
  - *(English)* "My date of birth is 2 November 1995. Money has been deducted from my account; I made no payment."
- **Mitr (expected, Hindi):** "आपकी पहचान सत्यापित हो गई है। 3 जून को दोपहर 2:46 बजे quickpay@okaxis को ₹14,999 का भुगतान हुआ है, जिसे संदिग्ध के रूप में चिह्नित किया गया है। कृपया तुरंत 1930 पर कॉल करें और 1800-123-4567 पर अपनी UPI ID ब्लॉक करवाएं। क्या मैं और कुछ देखूँ?"

**Turn 3 — `[मराठी]`** *(ask what to do now, in Marathi)*
- **Caller (Marathi):** "मला माझी UPI आत्ताच ब्लॉक करायची आहे. मी पुढे काय करू?"
  - *(roman)* "Mala majhi UPI aattaach block karaychi aahe. Mi pudhe kaay karu?"
  - *(English)* "I want to block my UPI right now. What should I do next?"
- **Mitr (expected, Marathi):** "लगेच 1930 या सायबर-क्राइम हेल्पलाइनवर कॉल करा, आणि 1800-123-4567 वर कॉल करून तुमची UPI ID ब्लॉक करा. त्यानंतर cybercrime.gov.in वर तक्रार नोंदवा. मी तुमच्यासाठी आणखी काही पाहू का?"

**Turn 4 — `[English]`** *(switch back to English)*
- **Caller:** "I also see a second attempt for the same amount — did that one go through?"
- **Mitr (expected, English):** "No — a second ₹14,999 attempt to the same payee at 2:48 PM on 3 June was declined by our fraud monitoring, so only the first one is disputed. Would you like me to confirm the next steps again?"

*Why this scene lands:* identity verification, then the agent reading Priya's **real** disputed transaction (₹14,999 → quickpay@okaxis) out of Elasticsearch, fraud guidance, and the failed second attempt — all while the caller freely switches English ↔ Hindi ↔ Marathi.

---

## 💸 SCENE 2 — Rajesh Kumar · "where is my money?" · English → Hindi
**Caller card:** Rajesh Kumar (Bengaluru) · **DOB:** 14 March 1988

**Turn 1 — `[English]`**
- **Caller:** "Hi, did my salary come this month, and where is my Flipkart refund?"
- **Mitr (expected, English):** "Happy to check. First, for your security, what is your date of birth?"

**Turn 2 — `[English]`**
- **Caller:** "14th March 1988."
- **Mitr (expected, English):** "Thanks, you're verified. Your salary of ₹1,20,000 from TechCorp was credited on 1 June. Your Flipkart refund of ₹2,499 is still processing and usually takes three to seven working days. Anything else I can check?"

**Turn 3 — `[हिंदी]`** *(switch to Hindi)*
- **Caller (Hindi):** "मेरी होम लोन की EMI इस महीने कट गई क्या? और मेरा बैलेंस कितना है?"
  - *(roman)* "Meri home loan ki EMI is mahine kat gayi kya? Aur mera balance kitna hai?"
  - *(English)* "Did my home-loan EMI get debited this month? And what's my balance?"
- **Mitr (expected, Hindi):** "हाँ, ₹38,500 की होम लोन EMI 2 जून को ऑटो-डेबिट हो गई है। आपका मौजूदा बैलेंस ₹1,41,342 है। क्या और कुछ बताऊँ?"

---

## 👵 SCENE 3 — Anil Verma · delayed pension · Hindi
**Caller card:** Anil Verma (Lucknow) · **DOB:** 21 July 1958

**Turn 1 — `[हिंदी]`**
- **Caller (Hindi):** "बेटा, मेरी इस महीने की पेंशन आई या नहीं? बहुत दिन हो गए।"
  - *(roman)* "Beta, meri is mahine ki pension aayi ya nahi? Bahut din ho gaye."
  - *(English)* "Has my pension for this month come in or not? It's been many days."
- **Mitr (expected, Hindi):** "ज़रूर देखता हूँ। सुरक्षा के लिए कृपया अपनी जन्मतिथि बताइए।"

**Turn 2 — `[हिंदी]`**
- **Caller (Hindi):** "इक्कीस जुलाई उन्नीस सौ अट्ठावन।"
  - *(roman)* "Ikkees July unnees-sau-atthaavan."
  - *(English)* "21 July 1958."
- **Mitr (expected, Hindi):** "आपकी ₹32,000 की पेंशन अभी प्रोसेस हो रही है — 3 जून को शुरू हुई है और जल्द ही जमा हो जाएगी। पिछले महीने की पेंशन सफलतापूर्वक जमा हुई थी। क्या मैं आपके लिए और कुछ देखूँ?"

---

## 📋 Data cheat-sheet (so the numbers always match)

| Caller | DOB (say this) | The "money" moment | Key figures |
|--------|----------------|--------------------|-------------|
| **Priya Sharma** (CUST1002) | 2 November 1995 | Disputed UPI fraud | ₹14,999 → `quickpay@okaxis`, 3 Jun 2:46 PM (2nd attempt 2:48 PM failed); salary ₹85,000; bal ₹1,09,200 |
| **Rajesh Kumar** (CUST1001) | 14 March 1988 | Salary in, refund pending | Salary ₹1,20,000 (1 Jun); EMI ₹38,500 (2 Jun); Flipkart refund ₹2,499 pending; bal ₹1,41,342 |
| **Anil Verma** (CUST1003) | 21 July 1958 | Pension delayed | Pension ₹32,000 PENDING; bal ₹42,250 |
| **Sunita Devi** (CUST1004) | 9 January 1991 | Refund pending | Meesho refund ₹2,499 pending; bal ₹7,800 |

> Note: routine transaction amounts/dates refresh every time the data is re-ingested
> (dynamic last-30-day window), but the **highlighted moments above stay fixed**, so the
> script always works.

## 🎥 Recording flow (suggested 2–3 min cut)
1. Open with **Scene 1** (Priya) — the language-switching fraud story is the showstopper.
2. Cut to **Scene 2** (Rajesh, English→Hindi) to show everyday "where's my refund/EMI".
3. Close with **Scene 3** (Anil, Hindi) — the pensioner moment is emotionally relatable.
4. Keep the **"behind the scenes"** panel expanded on at least one reply to show the
   English query hitting Elastic — that proves the Elastic-in-English design.
