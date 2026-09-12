# Decisions for Murad

Six items. Each is a genuine author decision: a choice where the evidence does
not settle the answer, or where the answer is editorial. Anything with an
objectively preferable technical resolution has been fixed rather than listed
here, and is recorded in `docs/REVIEW_NOTES.md`.

Nothing below blocks the rest of the correction work.

---

## 1. Tail-signal aggregation — which construction is primary

**Asked:** The published tail signal flags exceedances daily but reads them only
on Fridays, so 70 of the 105 weeks containing an exceedance enter the panel as
zeros. Two all-trading-days alternatives give different answers, and across the
three the skewness estimate **changes sign**.

**Options:** (a) keep the Friday-sampled construction as primary and report the
sensitivity; (b) adopt one alternative as primary; (c) present all three with no
primary.

**Recommendation: (a), which is what the branch does.** Both alternatives
redefine the signal rather than correct it, and choosing one after seeing its
result is the specification search this paper criticises. Your call is whether to
endorse that framing.

---

## 2. Execution timing — Friday close or Monday open

**Asked:** The published specification entered at the Monday open after Friday
signal generation; this revision enters at the Friday close. Daily bars carry an
Open column, so both are implementable and the choice is not a data limitation.
Across four timings the cumulative gross return ranges from −0.73% to −8.03%.

**Options:** (a) keep Friday close as the reported baseline with the grid as
robustness; (b) restore Monday open as the specification, making the grid's
Monday-open column the headline.

**Consequence if (b):** the analysis sample moves from 504 weeks to the grid's
common sample, and every headline figure in the paper changes. **Recommendation:
(a)**, but this is the single decision with the largest downstream effect and it
is properly yours. The pre-specified paired contrasts all include zero, so the
sample does not tell us which is right.

---

## 3. Entry-rule symmetrization — where it belongs

**Asked:** The long and short legs differ in four respects the manuscript never
argued for. Three symmetrizations were pre-specified and run; all four rules lose
money gross, with realised losses spanning 6.21 points.

**Options:** main text (current: new §4.6 and Table 12), appendix, or the
response letter only.

**Recommendation: keep it in the main text.** It is the most direct answer to
Reviewer 3's comment and the pre-registration is what makes it credible. Placement
is presentation, not evidence — decide on conceptual relevance, and note that the
reporting rule fixed in advance requires disclosure wherever it lands.

---

## 4. Raw data — commit it or not

**Asked:** The raw CSVs are currently gitignored and not committed. Exact
reproduction of the archived figures is therefore impossible without your files;
the pipeline caches inputs and records SHA-256 hashes and software versions
instead.

**Options:** (a) leave uncommitted, readers re-download and verify against the
manifest; (b) commit the CSVs.

**Recommendation: (a) unless you have checked Yahoo's redistribution terms.** This
is a licensing question about data you sourced, which is why it is yours and not
mine to settle. Seven of eight files reproduce byte-for-byte on an independent
download, so (a) is workable.

---

## 5. Version, DOI and supersession

**Asked:** The corrected results change every headline figure. The concept DOI
resolves to the latest version; v2.0.1 is deposited.

**Options:** (a) new version under the same concept DOI with a supersession note;
(b) withdraw and replace the deposited record.

**Recommendation: (a).** The published version should remain citable and visibly
superseded rather than disappear — a paper arguing for transparent correction
should not erase its own record. The mechanics are yours.

---

## 6. Standalone analysis scripts — form only

**Asked:** The execution-timing grid had been produced by a script that was never
committed, leaving 21 numbers in a headline exhibit with no traceable source.
**The defect is fixed**: the computation now lives in the pipeline and reproduces
every committed figure exactly.

**Options:** whether the repository should keep any standalone analysis scripts at
all, or require everything to run through `full_pipeline.py`.

**Recommendation: require the pipeline.** This is a repository-convention question
rather than a result; raised only because the convention is yours to set.

---

## Not asked of you

These were fixed rather than referred, because each had an objectively correct
resolution settled by the canonical output: three stale or mis-transcribed
statistics, an inferential claim stated as a realised one, a paragraph reasoning
from a superseded candidate universe, and the dead exit branch, double execution
lag and sizing defects from the first round. `docs/REVIEW_NOTES.md` records each
with its origin and class.

One small editorial item I intend to fix unless you object: `tab:gpd` is
referenced nowhere in the text. It should be cited where its numbers are
discussed, or cut.
