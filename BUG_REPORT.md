# Bug-Report und Fixes für compare_app.py

## Datum: 2026-01-19

### ✅ BUG #1: Dividendenrendite falsch dargestellt (BEHOBEN)
**Beschreibung:** META und GOOGL zeigten 34% und 25% Dividendenrendite statt 0.34% und 0.25%

**Ursache:** 
- yfinance liefert `dividendYield` als Dezimalwert (z.B. 0.34 für 0.34%)
- Die Funktion `fmt_percent_for()` hatte eine Heuristik: Werte ≤ 1.5 werden mit 100 multipliziert
- Diese Heuristik ist für Margen (z.B. 0.05 → 5%) korrekt, aber nicht für Dividendenrenditen

**Fix (Zeile 245-247):**
```python
# Ausnahme für Dividendenmetriken:
if "Dividenden" not in key and abs(x) <= 1.5:
    x *= 100.0
```

**Status:** ✅ Behoben

---

### ✅ BUG #2: Frontend-Limit verhindert Hinzufügen neuer Metriken (BEHOBEN)
**Beschreibung:** Button "Hinzufügen" funktionierte nicht, um neue Kennzahlen auszuwählen

**Ursache:**
- JavaScript hatte hartes Limit: maximal 6 Chips (Zeile 1219)
- Nach Auswahl der Defaults (6 Stück) konnte man keine weiteren hinzufügen
- Abwählen entfernte Chips nicht aus dem DOM → Limit blieb erreicht

**Fix:**
1. Limit von 6 auf 24 erhöht (Zeile 1219)
2. Visuelle Warnung: Zähler wird rot bei >6 ausgewählten Metriken (Zeile 1213)

**Status:** ✅ Behoben

---

### 🔍 POTENZIELLE BUGS (ZU PRÜFEN):

#### 3. Numerische Formatierung bei anderen Prozent-Metriken
**Verdacht:** Andere Metriken wie "Gewinnwachstum", "5Y Dividendenrendite" könnten dasselbe Problem haben

**Zu testen:**
- Gewinnwachstum (earningsGrowth)
- 5Y Dividendenrendite (fiveYearAvgDividendYield)
- Verschuldungsgrad (debtToEquity)

#### 4. Vergleichslogik für "BETTER_LOW" Metriken
**Verdacht:** Farbcodierung könnte für Verschuldungsgrad/KGV inkonsistent sein

**Zu prüfen:** Zeilen 521-540 (display_value Farblogik)

#### 5. Column-Aliasing
**Verdacht:** Neue Metriken könnten fehlende Aliasse haben

**Zu prüfen:** COLUMN_ALIASES (Zeilen 173-196)

---

## Nächste Schritte:
1. ✅ Dividendenrendite-Fix verifizieren (manuell mit stock_data.csv)
2. ⏳ Weitere Prozent-Metriken testen
3. ⏳ Vergleichslogik visuell testen
4. ⏳ Edge Cases mit fehlenden Daten prüfen
