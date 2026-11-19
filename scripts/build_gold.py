# Build the frozen 30-question gold set from the formal corpus.
# Quotes are sliced from the loaded text. This script does not edit the corpus.

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.retrieval.types import file_hash, formal_loader

CORPUS_VERSION = "794e3d1956fc324659da149d5bfb0e083d257845895057b631d4578ec5b29795"
FORMAL = ROOT / "data" / "formal_corpus"
GOLD_PATH = ROOT / "data" / "eval" / "gold.jsonl"
MANIFEST_PATH = ROOT / "data" / "eval" / "manifest.json"
FIELDS = (
    "case_id",
    "corpus_version",
    "question",
    "question_type",
    "should_refuse",
    "reference_answer",
    "key_facts",
    "evidence",
    "refusal_reason",
)


class Progress:
    """实时进度与剩余时间。

    示例:
        progress = Progress(total=30)
        progress.advance()
    输出格式: [Progress]  3.33% Elapsed: 00:00:01 Remaining: 00:00:29
    """

    def __init__(self, total: int) -> None:
        self.total = max(int(total), 1)
        self.done = 0
        self.started = time.monotonic()
        self._render()

    def advance(self) -> None:
        self.done += 1
        self._render()

    def finish(self) -> None:
        self.done = self.total
        self._render(final=True)

    def _render(self, final: bool = False) -> None:
        elapsed = time.monotonic() - self.started
        ratio = min(self.done / self.total, 1.0)
        remaining = 0.0 if ratio <= 0 or ratio >= 1 else elapsed * (1 - ratio) / ratio
        print(
            f"\r[Progress] {ratio * 100:6.2f}% Elapsed: {format_duration(elapsed)} Remaining: {format_duration(remaining)}",
            end="",
            flush=True,
        )
        if final:
            print(flush=True)


def format_duration(seconds: float) -> str:
    whole = max(0, int(seconds + 0.5))
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def fail(message: str) -> None:
    print(f"build_gold.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_documents() -> dict[str, dict]:
    manifest = json.loads((FORMAL / "manifest.json").read_text(encoding="utf-8"))
    corpus_manifest = json.loads((ROOT / "data" / "corpus_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("corpus_version") != CORPUS_VERSION or corpus_manifest.get("corpus_version") != CORPUS_VERSION:
        fail("formal corpus version does not match the frozen version; the corpus was not modified")
    documents = formal_loader(FORMAL)(CORPUS_VERSION)
    if len(documents) != 5 or len({doc["document_id"] for doc in documents}) != 5:
        fail("formal_loader did not return five unique documents")
    if sum(len(doc["articles"]) for doc in documents) != 121:
        fail("formal_loader did not return 121 main articles")
    return {doc["document_id"]: doc for doc in documents}


def structure_span(document_id: str, structure_id: str) -> tuple[int, int]:
    accepted = json.loads((ROOT / "data" / "processed" / f"{document_id}.json").read_text(encoding="utf-8"))
    found: list[tuple[int, int]] = []

    def consider(item: dict, key: str) -> None:
        if item.get(key) == structure_id:
            found.append((item["start"], item["end"]))

    for article in accepted["articles"]:
        consider(article, "article_id")
    for annex in accepted.get("annexes", []):
        consider(annex, "structure_id")
    for chapter in accepted.get("chapters", []):
        consider(chapter, "structure_id")
        for section in chapter.get("sections") or []:
            consider(section, "structure_id")
    if len(found) != 1:
        fail(f"{document_id} {structure_id}: expected one structure span, found {len(found)}")
    return found[0]


def clip(documents: dict[str, dict], document_id: str, structure_id: str, start_anchor: str, end_anchor: str) -> dict:
    start, end = structure_span(document_id, structure_id)
    text = documents[document_id]["text"]
    region = text[start:end]
    start_at = region.find(start_anchor)
    if start_at < 0 or region.find(start_anchor, start_at + 1) >= 0:
        fail(f"{structure_id}: start anchor is not unique: {start_anchor!r}")
    end_at = region.find(end_anchor, start_at)
    if end_at < 0 or region.find(end_anchor, end_at + 1) >= 0:
        fail(f"{structure_id}: end anchor is not unique after the start anchor: {end_anchor!r}")
    quote_start = start + start_at
    quote_end = start + end_at + len(end_anchor)
    quote = text[quote_start:quote_end]
    if not 0 < len(quote) < 400:
        fail(f"{structure_id}: quote length {len(quote)} is outside 1..399")
    if "\n" in quote and quote.count("\n") > 2:
        fail(f"{structure_id}: quote crosses more than two line breaks")
    evidence = {"document_id": document_id, "start": quote_start, "end": quote_end, "quote": quote}
    if ":article:" in structure_id:
        evidence = {
            "document_id": document_id,
            "article_id": structure_id,
            "start": quote_start,
            "end": quote_end,
            "quote": quote,
        }
    else:
        evidence = {
            "document_id": document_id,
            "structure_id": structure_id,
            "start": quote_start,
            "end": quote_end,
            "quote": quote,
        }
    return evidence


def answer(case_id: str, question_type: str, question: str, reference: str, evidence: list[dict]) -> dict:
    if question_type == "single_article" and len(evidence) != 1:
        fail(f"{case_id}: single_article requires one evidence segment")
    if question_type == "multi_evidence" and len(evidence) < 2:
        fail(f"{case_id}: multi_evidence requires at least two evidence segments")
    return {
        "case_id": case_id,
        "corpus_version": CORPUS_VERSION,
        "question": question,
        "question_type": question_type,
        "should_refuse": False,
        "reference_answer": reference,
        "key_facts": [item["quote"] for item in evidence],
        "evidence": evidence,
        "refusal_reason": None,
    }


def refuse(case_id: str, question: str, reason: str) -> dict:
    return {
        "case_id": case_id,
        "corpus_version": CORPUS_VERSION,
        "question": question,
        "question_type": "unanswerable",
        "should_refuse": True,
        "reference_answer": "The frozen five-document corpus does not contain sufficient information to answer this question.",
        "key_facts": [],
        "evidence": [],
        "refusal_reason": reason,
    }


def build_cases(documents: dict[str, dict]) -> list[dict]:
    crd = "eu_consumer_rights_2011_83"
    sgd = "eu_sale_of_goods_2019_771"
    dcd = "eu_digital_content_2019_770"
    ucpd = "eu_unfair_practices_2005_29"
    utd = "eu_unfair_terms_93_13"
    cases = [
        answer(
            "gold-crd-delivery-time",
            "single_article",
            "The parties to a sales contract have not agreed when the goods will be delivered. Under the original text of Directive 2011/83/EU, what is the trader's delivery obligation?",
            "The trader must deliver the goods by transferring physical possession or control to the consumer without undue delay, and not later than 30 days from the conclusion of the contract.",
            [clip(documents, crd, f"{crd}:article:18", "1. Unless the parties have agreed otherwise on the time of delivery", "from the conclusion of the contract.")],
        ),
        answer(
            "gold-crd-withdrawal-refund",
            "multi_evidence",
            "A consumer withdraws from a distance contract under Directive 2011/83/EU and tells the trader in accordance with Article 11. What payments must the trader reimburse, and by when?",
            "The trader must reimburse all payments received from the consumer, including delivery costs where applicable, without undue delay and not later than 14 days after being informed of the withdrawal. The trader need not reimburse supplementary delivery costs if the consumer expressly chose a delivery type other than the least expensive standard delivery offered by the trader. For a sales contract, unless the trader has offered to collect the goods, the trader may withhold that reimbursement until the goods are received back or the consumer supplies evidence of having sent them back, whichever is earliest.",
            [
                clip(documents, crd, f"{crd}:article:13", "1. The trader shall reimburse all payments received from the consumer", "in accordance with Article 11."),
                clip(documents, crd, f"{crd}:article:13", "2. Notwithstanding paragraph 1, the trader shall not be required to reimburse the supplementary costs", "least expensive type of standard delivery offered by the trader."),
                clip(documents, crd, f"{crd}:article:13", "3. Unless the trader has offered to collect the goods himself", "whichever is the earliest."),
            ],
        ),
        answer(
            "gold-crd-payment-fee-cap",
            "single_article",
            "Under Directive 2011/83/EU, may a trader charge the consumer a fee for using a particular means of payment that is higher than the trader's own cost of accepting that means?",
            "No. Member States must prohibit traders from charging consumers, for the use of a given means of payment, fees that exceed the cost borne by the trader for the use of that means.",
            [clip(documents, crd, f"{crd}:article:19", "Member States shall prohibit traders from charging consumers", "for the use of such means.")],
        ),
        answer(
            "gold-crd-withdrawal-information-omission",
            "single_article",
            "A trader concludes a distance contract covered by Directive 2011/83/EU but never gives the consumer the withdrawal information required by Article 6(1)(h). When does the withdrawal period expire?",
            "It expires 12 months from the end of the initial withdrawal period determined under Article 9(2).",
            [clip(documents, crd, f"{crd}:article:10", "1. If the trader has not provided the consumer with the information on the right of withdrawal", "in accordance with Article 9(2).")],
        ),
        answer(
            "gold-crd-withdrawal-digital-content",
            "multi_evidence",
            "Does Directive 2011/83/EU always give a consumer 14 days to withdraw from a distance contract for digital content that is not supplied on a tangible medium?",
            "No. Article 9(1) gives 14 days to withdraw from a distance or off-premises contract without giving a reason, but only where an Article 16 exception does not apply. Article 16(m) excludes that right once performance of digital content not supplied on a tangible medium has begun with the consumer's prior express consent and acknowledgment that the right of withdrawal is lost.",
            [
                clip(documents, crd, f"{crd}:article:9", "1. Save where the exceptions provided for in Article 16 apply", "Article 13(2) and Article 14."),
                clip(documents, crd, f"{crd}:article:16", "(m) the supply of digital content which is not supplied on a tangible medium", "loses his right of withdrawal."),
            ],
        ),
        answer(
            "gold-crd-late-delivery-termination",
            "multi_evidence",
            "Under Directive 2011/83/EU, the parties did not agree a delivery date. The trader misses the Article 18(1) delivery period. The consumer then sets an additional period appropriate to the circumstances, and the trader still does not deliver. May the consumer terminate, and what must the trader reimburse?",
            "Yes. If the trader does not deliver within that additional period, the consumer may terminate the contract. Upon termination, the trader must reimburse all sums paid under the contract without undue delay. This answer concerns that additional-period route.",
            [
                clip(documents, crd, f"{crd}:article:18", "2. Where the trader has failed to fulfil his obligation to deliver the goods", "appropriate to the circumstances."),
                clip(documents, crd, f"{crd}:article:18", "If the trader fails to deliver the goods within that additional period of time", "entitled to terminate the contract."),
                clip(documents, crd, f"{crd}:article:18", "3. Upon termination of the contract", "all sums paid under the contract."),
            ],
        ),
        answer(
            "gold-sgd-two-year-liability",
            "multi_evidence",
            "Under the original text of Directive (EU) 2019/771, for how long is a seller liable for a lack of conformity that already exists when the goods are delivered? May a Member State provide a longer period, and may the period be shorter for second-hand goods?",
            "The seller is liable where that lack of conformity becomes apparent within two years of delivery. Without prejudice to Article 7(3), that rule also applies to goods with digital elements. Member States may maintain or introduce longer time limits than those in Article 10(1) and (2). For second-hand goods, Member States may allow the seller and the consumer to agree a shorter liability or limitation period than those in paragraphs 1, 2 and 5, but that shorter period must not be less than one year.",
            [
                clip(documents, sgd, f"{sgd}:article:10", "1. The seller shall be liable to the consumer for any lack of conformity", "goods with digital elements."),
                clip(documents, sgd, f"{sgd}:article:10", "3. Member States may maintain or introduce longer time limits", "in paragraphs 1 and 2."),
                clip(documents, sgd, f"{sgd}:article:10", "6. Member States may provide that, in the case of second-hand goods", "shall not be less than one year."),
            ],
        ),
        answer(
            "gold-sgd-one-year-presumption",
            "single_article",
            "A lack of conformity in goods covered by Directive (EU) 2019/771 becomes apparent eight months after delivery. What does Article 11(1) presume, and when does that presumption not apply?",
            "It presumes that the lack of conformity existed at delivery, including for goods with digital elements, unless the contrary is proved or the presumption is incompatible with the nature of the goods or the nature of the lack of conformity.",
            [clip(documents, sgd, f"{sgd}:article:11", "1. Any lack of conformity which becomes apparent within one year", "goods with digital elements.")],
        ),
        answer(
            "gold-sgd-repair-or-replacement",
            "multi_evidence",
            "Goods sold under Directive (EU) 2019/771 are not in conformity. May the consumer choose between repair and replacement, and must that remedy be free of charge?",
            "The consumer may choose repair or replacement in order to have the goods brought into conformity, unless the chosen remedy is impossible or would impose disproportionate costs on the seller in the circumstances listed in Article 13(2). Where repair or replacement is used, it must be carried out free of charge, within a reasonable time after the seller is informed, and without significant inconvenience to the consumer.",
            [
                clip(documents, sgd, f"{sgd}:article:13", "2. In order to have the goods brought into conformity, the consumer may choose between repair and replacement", "including:"),
                clip(documents, sgd, f"{sgd}:article:14", "1. Repairs or replacements shall be carried out:", "(a) free of charge;"),
                clip(documents, sgd, f"{sgd}:article:14", "(b) within a reasonable period of time from the moment the seller has been informed", "required the goods."),
            ],
        ),
        answer(
            "gold-sgd-minor-lack-no-termination",
            "single_article",
            "Under Directive (EU) 2019/771, may a consumer terminate the sales contract when the lack of conformity is only minor?",
            "No. The consumer is not entitled to terminate if the lack of conformity is only minor, and the seller bears the burden of proving that it is minor.",
            [clip(documents, sgd, f"{sgd}:article:13", "5. The consumer shall not be entitled to terminate the contract if the lack of conformity is only minor.", "shall be on the seller.")],
        ),
        answer(
            "gold-sgd-price-reduction",
            "single_article",
            "How does Directive (EU) 2019/771 measure a price reduction for goods that are not in conformity?",
            "The reduction must be proportionate to the decrease in the value of the goods received by the consumer compared with the value the goods would have had if they had been in conformity.",
            [clip(documents, sgd, f"{sgd}:article:15", "The reduction of price shall be proportionate", "if they were in conformity.")],
        ),
        answer(
            "gold-dcd-supply-without-delay",
            "single_article",
            "A contract covered by the original text of Directive (EU) 2019/770 does not say when the trader will supply a digital service. When must the trader supply it?",
            "Unless the parties have agreed otherwise, the trader must supply the digital content or digital service without undue delay after the conclusion of the contract.",
            [clip(documents, dcd, f"{dcd}:article:5", "1. The trader shall supply the digital content or digital service to the consumer.", "after the conclusion of the contract.")],
        ),
        answer(
            "gold-dcd-burden-of-supply",
            "single_article",
            "Under Directive (EU) 2019/770, who must prove that the digital content or digital service was supplied as Article 5 requires?",
            "The burden of proof is on the trader.",
            [clip(documents, dcd, f"{dcd}:article:12", "1. The burden of proof with regard to whether the digital content or digital service was supplied", "shall be on the trader.")],
        ),
        answer(
            "gold-dcd-conformity-remedies",
            "multi_evidence",
            "Digital content covered by Directive (EU) 2019/770 and supplied in exchange for a price is not in conformity. What remedies does Article 14 provide, and when is termination unavailable because the defect is minor?",
            "The consumer is entitled to have the digital content or service brought into conformity, to a proportionate price reduction, or to terminate the contract, under the conditions in Article 14. Where a price is paid, the consumer may terminate only if the lack of conformity is not minor, and the trader bears the burden of proving that it is minor.",
            [
                clip(documents, dcd, f"{dcd}:article:14", "1. In the case of a lack of conformity, the consumer shall be entitled", "under the conditions set out in this Article."),
                clip(documents, dcd, f"{dcd}:article:14", "6. Where the digital content or digital service is supplied in exchange for the payment of a price", "shall be on the trader."),
            ],
        ),
        answer(
            "gold-dcd-reimbursement-time",
            "single_article",
            "A consumer covered by Directive (EU) 2019/770 tells the trader that the consumer is terminating the contract because the digital service is not in conformity. How quickly must the trader make a reimbursement owed under Article 14 or Article 16?",
            "The trader must reimburse the consumer without undue delay and, in any event, within 14 days of being informed of the consumer's decision to invoke the price reduction or to terminate.",
            [clip(documents, dcd, f"{dcd}:article:18", "1. Any reimbursement that is owed to the consumer by the trader", "or to terminate the contract.")],
        ),
        answer(
            "gold-dcd-modification-conditions",
            "multi_evidence",
            "A contract under Directive (EU) 2019/770 supplies a digital service over a period of time. The trader wants to modify it beyond what is necessary to keep it in conformity with Articles 7 and 8. Which conditions in Article 19(1) must be met?",
            "The contract must allow the modification and provide a valid reason for it. The modification must be made without additional cost to the consumer. The consumer must be informed of the modification in a clear and comprehensible manner. Where paragraph 2 applies, the consumer must also be informed reasonably in advance, on a durable medium, of the features and timing of the modification and of the right to terminate or of the possibility to keep the service without the modification.",
            [
                clip(documents, dcd, f"{dcd}:article:19", "1. Where the contract provides that the digital content or digital service is to be supplied or made accessible", "if the following conditions are met:"),
                clip(documents, dcd, f"{dcd}:article:19", "(a) the contract allows, and provides a valid reason for, such a modification;", "such a modification;"),
                clip(documents, dcd, f"{dcd}:article:19", "(b) such a modification is made without additional cost to the consumer;", "cost to the consumer;"),
                clip(documents, dcd, f"{dcd}:article:19", "(c) the consumer is informed in a clear and comprehensible manner of the modification; and", "of the modification; and"),
                clip(documents, dcd, f"{dcd}:article:19", "(d) in the cases referred to in paragraph 2", "in accordance with paragraph 4."),
            ],
        ),
        answer(
            "gold-ucpd-two-part-unfairness-test",
            "single_article",
            "Under the original text of Directive 2005/29/EC, when is a commercial practice unfair under the general test in Article 5(2)?",
            "It is unfair when both connected parts are met: it is contrary to the requirements of professional diligence, and it materially distorts, or is likely to materially distort, the economic behaviour of the average consumer it reaches or to whom it is addressed, or of the average member of the group when it is directed to a particular group.",
            [clip(documents, ucpd, f"{ucpd}:article:5", "(a) it is contrary to the requirements of professional diligence,", "particular group of consumers.")],
        ),
        answer(
            "gold-ucpd-aggressive-practice",
            "multi_evidence",
            "What must be shown before Directive 2005/29/EC treats a commercial practice as aggressive?",
            "In its factual context, and taking account of all its features and circumstances, the practice must use harassment, coercion, including physical force, or undue influence. It must significantly impair, or be likely to significantly impair, the average consumer's freedom of choice or conduct with regard to the product, and thereby cause or be likely to cause a transactional decision that the consumer would not otherwise have taken.",
            [
                clip(documents, ucpd, f"{ucpd}:article:8", "A commercial practice shall be regarded as aggressive if", "or undue influence,"),
                clip(documents, ucpd, f"{ucpd}:article:8", "it significantly impairs or is likely to significantly impair", "would not have taken otherwise."),
            ],
        ),
        answer(
            "gold-ucpd-invitation-price-information",
            "multi_evidence",
            "A trader makes an invitation to purchase covered by Directive 2005/29/EC, and the price information is not already apparent. What price information does Article 7 treat as material?",
            "The price inclusive of taxes is material. If the price cannot reasonably be calculated in advance, the manner of calculating it is material, together with additional freight, delivery or postal charges where appropriate, or the fact that such charges may be payable where those charges also cannot reasonably be calculated in advance.",
            [
                clip(documents, ucpd, f"{ucpd}:article:7", "4. In the case of an invitation to purchase", "not already apparent from the context:"),
                clip(documents, ucpd, f"{ucpd}:article:7", "(c) the price inclusive of taxes", "charges may be payable;"),
            ],
        ),
        answer(
            "gold-ucpd-pyramid-scheme",
            "multi_evidence",
            "Under Directive 2005/29/EC, is a pyramid promotional scheme described in Annex I unfair only after a case-by-case assessment, or in all circumstances?",
            "Annex I, point 14, covers establishing, operating or promoting a pyramid scheme in which a consumer gives consideration for the opportunity to receive compensation derived primarily from introducing other consumers rather than from the sale or consumption of products. Article 5(5) says the Annex I practices are unfair in all circumstances. The same list applies in every Member State and may be changed only by revision of the Directive.",
            [
                clip(documents, ucpd, f"{ucpd}:article:5", "5. Annex I contains the list of those commercial practices", "by revision of this Directive."),
                clip(documents, ucpd, f"{ucpd}:annex:I", "14. Establishing, operating or promoting a pyramid promotional scheme", "sale or consumption of products."),
            ],
        ),
        answer(
            "gold-utd-unfair-term-test",
            "multi_evidence",
            "Under Council Directive 93/13/EEC, when is a contract term regarded as unfair, and when is a term treated as not individually negotiated?",
            "A term that has not been individually negotiated is unfair if, contrary to good faith, it causes a significant imbalance in the parties' rights and obligations under the contract, to the detriment of the consumer. A term is always regarded as not individually negotiated where it was drafted in advance and the consumer has not been able to influence its substance, particularly in a pre-formulated standard contract.",
            [
                clip(documents, utd, f"{utd}:article:3", "1. A contractual term which has not been individually negotiated shall be regarded as unfair", "to the detriment of the consumer."),
                clip(documents, utd, f"{utd}:article:3", "2. A term shall always be regarded as not individually negotiated", "particularly in the context of a pre-formulated standard contract."),
            ],
        ),
        answer(
            "gold-utd-plain-language",
            "single_article",
            "A seller offers a consumer a written standard contract covered by Directive 93/13/EEC. What does Article 5 require for the wording, and how is doubt about a term resolved?",
            "The written terms must always be drafted in plain, intelligible language. If there is doubt about the meaning of a term, the interpretation most favourable to the consumer prevails. That interpretation rule does not apply in the procedures laid down in Article 7(2).",
            [clip(documents, utd, f"{utd}:article:5", "In the case of contracts where all or certain terms offered to the consumer are in writing", "Article 7 (2).")],
        ),
        answer(
            "gold-utd-unfair-term-not-binding",
            "single_article",
            "Under Directive 93/13/EEC, what effect must national law give to an unfair term in a consumer contract, and what happens to the rest of the contract?",
            "Member States must provide that an unfair term used in a contract with a consumer is, as provided for under their national law, not binding on the consumer. The contract continues to bind the parties on the remaining terms if it is capable of continuing in existence without the unfair terms.",
            [clip(documents, utd, f"{utd}:article:6", "1. Member States shall lay down that unfair terms used in a contract", "without the unfair terms.")],
        ),
        answer(
            "gold-utd-negotiation-burden",
            "single_article",
            "A seller claims that a standard term in a consumer contract covered by Directive 93/13/EEC was individually negotiated. Who must prove that claim?",
            "The seller or supplier who makes that claim bears the burden of proof.",
            [clip(documents, utd, f"{utd}:article:3", "Where any seller or supplier claims that a standard term has been individually negotiated", "shall be incumbent on him.")],
        ),
        refuse(
            "gold-refuse-air-cancellation-amount",
            "What fixed amount in euro must an air carrier pay a passenger when it cancels a flight?",
            "None of the five frozen directives states a fixed euro amount payable by an air carrier for cancellation of a flight. Directive 2011/83/EU excludes passenger transport services from its scope except Article 8(2) and Articles 19 and 22, and those provisions concern information, payment fees and additional payments rather than a cancellation tariff. A recital mentions a compensation regime for service aspects of mixed contracts but states no airline amount. The goods, digital-content, unfair-term and unfair-practice directives do not set one either.",
        ),
        refuse(
            "gold-refuse-standard-vat-rate",
            "What standard percentage of value added tax must a trader add to the price of consumer goods?",
            "The frozen corpus contains no value-added-tax rate and no rule stating the percentage a trader must add. Price provisions, such as the requirement that an invitation to purchase show the price inclusive of taxes, do not state a tax percentage.",
        ),
        refuse(
            "gold-refuse-refund-interest-rate",
            "What annual statutory interest rate must a trader add when reimbursing a consumer under Article 13 of Directive 2011/83/EU?",
            "Article 13 of Directive 2011/83/EU requires reimbursement of the payments it identifies and, in a later paragraph, use of the same means of payment without fees, but it states no interest rate. The other directives state reimbursement periods or prohibit fees on reimbursement, and the Annex to Directive 93/13/EEC discusses contract terms about interest charged for financial services. None of those provisions sets a statutory annual rate on an Article 13 reimbursement.",
        ),
        refuse(
            "gold-refuse-german-fine",
            "What maximum fine in euro must Germany impose on a trader for using one unfair term in a consumer contract?",
            "The penalty provisions in the frozen directives require Member States to provide effective, proportionate and dissuasive penalties or enforcement measures. They do not name Germany, and they do not set a maximum fine in euro for using an unfair term.",
        ),
        refuse(
            "gold-refuse-lawsuit-deadline",
            "How many days after a seller refuses repair does Directive (EU) 2019/771 require a consumer to file a lawsuit before the claim is lost?",
            "Directive (EU) 2019/771 makes the seller liable for a lack of conformity that becomes apparent within the periods in Article 10 and allows Member States to attach limitation periods to the remedies, provided those periods still let the consumer exercise them. It does not require a lawsuit, name a court, or state a number of days after refusal of repair by which proceedings must be filed.",
        ),
        refuse(
            "gold-refuse-package-insurance",
            "What minimum insurance cover must a package-travel organiser hold for a consumer's trip?",
            "Directive 2011/83/EU places contracts within the package-travel directive outside its scope, and Directive 2005/29/EC lists package-travel legislation among sectoral information rules in Annex II. Neither provision, nor the goods, digital-content or unfair-term directives, states a minimum insurance amount or cover for a package-travel organiser.",
        ),
    ]
    return cases


def coverage(cases: list[dict]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for case in cases:
        if case["should_refuse"]:
            continue
        seen = set()
        for item in case["evidence"]:
            document_id = item["document_id"]
            bucket = counts.setdefault(document_id, {"answerable_questions": 0, "evidence_segments": 0})
            bucket["evidence_segments"] += 1
            seen.add(document_id)
        for document_id in seen:
            counts[document_id]["answerable_questions"] += 1
    return dict(sorted(counts.items()))


def render_jsonl(cases: list[dict]) -> str:
    lines = []
    for case in cases:
        if tuple(case) != FIELDS:
            fail(f"{case['case_id']}: field order changed")
        lines.append(json.dumps(case, ensure_ascii=False, separators=(", ", ": ")))
    return "\n".join(lines) + "\n"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    progress = Progress(3)
    documents = load_documents()
    progress.advance()
    cases = build_cases(documents)
    if len(cases) != 30 or len({case["case_id"] for case in cases}) != 30:
        fail("expected 30 unique case ids")
    answerable = [case for case in cases if not case["should_refuse"]]
    refusals = [case for case in cases if case["should_refuse"]]
    if len(answerable) != 24 or len(refusals) != 6:
        fail("expected 24 answerable questions and 6 refusals")
    rendered = render_jsonl(cases)
    if "\r" in rendered or not rendered.endswith("\n"):
        fail("gold jsonl must use LF and end with one newline")
    GOLD_PATH.write_bytes(rendered.encode("utf-8"))
    digest = file_hash(GOLD_PATH)
    progress.advance()
    type_counts: dict[str, int] = {}
    for case in cases:
        type_counts[case["question_type"]] = type_counts.get(case["question_type"], 0) + 1
    manifest = {
        "schema_version": "1.0",
        "kind": "gold_set",
        "corpus_version": CORPUS_VERSION,
        "gold_version": digest,
        "gold_path": "data/eval/gold.jsonl",
        "gold_sha256": digest,
        "question_count": 30,
        "answerable_count": 24,
        "refusal_count": 6,
        "question_types": dict(sorted(type_counts.items())),
        "coverage": coverage(cases),
        "version_algorithm": {
            "gold_version": "SHA-256 of the raw UTF-8 bytes of data/eval/gold.jsonl, including its final LF.",
            "excluded_from_fingerprint": ["gold_version", "gold_sha256", "exported_at"],
            "note": "The jsonl does not contain gold_version or a timestamp. Changing any question, answer, or evidence changes the file bytes and therefore gold_version.",
        },
        "loader": "app.retrieval.types.formal_loader",
        "loader_data_dir": "data/formal_corpus",
        "provenance": "Drafted with AI assistance and checked by slicing the frozen clean text. No human review is recorded. Formal retrieval results were not consulted.",
    }
    from app.retrieval.types import write_json

    write_json(MANIFEST_PATH, manifest)
    if file_hash(GOLD_PATH) != digest:
        fail("gold.jsonl hash changed after the manifest was prepared")
    progress.advance()
    progress.finish()
    print(f"corpus_version={CORPUS_VERSION}")
    print(f"gold_version={digest}")
    print(f"questions={len(cases)} answerable={len(answerable)} refusal={len(refusals)}")
    print("result=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
