+++
title = "What It Actually Takes to Fine-Tune an LLM in Europe"
date = "2026-02-13"
draft = false
tags = ["ai", "europe", "sovereignty", "fine-tuning", "copyright", "regulation"]
series = ["european-ai-sovereignty"]
+++

This series has so far dealt with deployment. [Where to host models](/posts/european-ai-sovereignty/), [how to wrap them in compliance logic](/posts/compliance-as-code-two-europes/), [which providers can serve inference](/posts/sovereign-inference-stack/), and [how to verify the supply chain](/posts/securing-open-source-ai-supply-chain/). All of that assumes you already have a model worth deploying.

This post goes earlier in the pipeline. What happens when you want to fine-tune a foundation model on proprietary data, and you need that model to be legal in both the UK and the EU?

The answer is more complicated than I expected. Copyright law, data protection, and AI-specific regulation each impose their own constraints on the fine-tuning process, and the UK and EU have diverged on all three. The result is a compliance surface that sits not at inference time (where the previous posts focused) but at training time, before a single weight has been updated.

---

## Do You Have the Right to Use That Data?

The basic act of fine-tuning involves feeding data into a model to adjust its weights. If that data is protected by copyright, you need a legal basis to use it. This is where the two jurisdictions split sharply.

### The EU Position

The EU's [Digital Single Market Directive (2019/790)](https://eur-lex.europa.eu/eli/dir/2019/790/oj) introduced two text and data mining (TDM) exceptions. [Article 3](https://eur-lex.europa.eu/eli/dir/2019/790/oj) is narrow: it covers research organisations and cultural heritage institutions doing scientific research. No opt-out permitted. Most commercial fine-tuning operations do not qualify.

[Article 4](https://eur-lex.europa.eu/eli/dir/2019/790/oj) is the one that matters. It provides a broad TDM exception for any purpose, including commercial model training, as long as you have lawful access to the content. The catch: rightsholders can opt out. For content available online, that opt-out must be expressed in "machine-readable means."

So in the EU, the default position is that you *can* mine copyrighted works for training, unless the rightsholder has explicitly reserved their rights. The burden is on the rightsholder to opt out, and on you to detect and respect that opt-out.

| | Article 3 | Article 4 |
| --- | --- | --- |
| **Who benefits** | Research organisations, cultural heritage institutions | Anyone, including commercial companies |
| **Permitted purpose** | Scientific research | Any purpose, including commercial training |
| **Rightsholder control** | No opt-out. Mandatory exception | Opt-out via express reservation of rights |
| **Reservation format** | Not applicable | Machine-readable means for online content |

### The UK Position

The UK did not implement the DSM Directive before Brexit. Its current law is [Section 29A of the Copyright, Designs and Patents Act 1988](https://www.legislation.gov.uk/ukpga/1988/48/section/29A), which permits text and data mining solely for non-commercial research.

That is it. There is no commercial TDM exception in UK law.

For commercial fine-tuning on copyrighted material in the UK, you need a licence from the rightsholder. Full stop.

The government ran a [consultation from December 2024 to February 2025](https://www.gov.uk/government/consultations/copyright-and-artificial-intelligence) presenting four options: maintain the status quo, strengthen copyright further, introduce a broad exception with no opt-out, or introduce an exception with an opt-out mechanism (mirroring EU Article 4). Option 3 (the opt-out model) was the government's preferred path.

The consultation received over 11,500 responses. 88% of those using the government's online platform backed Option 1: *stronger* copyright protection, not weaker. The UK creative sector made its feelings rather clear.

Rather than legislate immediately, the government punted. The [Data (Use and Access) Act 2025](https://www.legislation.gov.uk/ukpga/2025/1/contents/enacted) (Royal Assent, June 2025) mandates two reports by March 2026: an economic impact assessment of the four options ([Section 135](https://www.legislation.gov.uk/ukpga/2025/1/section/135)) and a comprehensive report on the use of copyright works in AI development ([Section 136](https://www.legislation.gov.uk/ukpga/2025/1/section/136)). Technical working groups are exploring transparency standards, crawler disclosure requirements, and licensing frameworks.

The practical consequence: commercial TDM in the UK remains legally uncertain until at least mid-2026. If you are fine-tuning on copyrighted content for commercial purposes, you need a licence or you are taking a risk.

### What This Means for Cross-Border Work

If you are building a model for both markets, the UK's stricter position wins. You cannot rely on the EU's Article 4 exception and then deploy in a jurisdiction that does not recognise it. The superset approach from [the earlier compliance-as-code post](/posts/compliance-as-code-two-europes/) applies here too: target the highest bar. In practice, that means treating all copyrighted training data as requiring a licence, and using automated opt-out detection as an additional safeguard for EU-sourced web content.

---

## The Opt-Out Detection Problem

Even in the EU, where Article 4 provides a broad exception, you still need to respect opt-outs. This sounds simple. It is not.

The DSM Directive says opt-outs for online content must be expressed in "machine-readable means." But it never defined what that means technically. Member states transposed the rules into national law without harmonising the technical standards. The result is a mess.

### What Counts as Machine-Readable?

There are several candidates:

- **robots.txt**: The oldest web standard for controlling crawler behaviour. Many publishers have added AI-specific directives (`User-agent: GPTBot`, `User-agent: CCBot`). This is the most widely adopted mechanism but was never designed for copyright reservation.

- **ai.txt**: A newer proposed standard specifically for communicating AI training permissions. Less widely adopted.

- **TDM Reservation Protocol (TDMRep)**: A [W3C community group specification](https://www.w3.org/community/tdmrep/) that uses HTTP headers and JSON-LD metadata to express rights reservations. The closest thing to a proper standard, but adoption remains limited.

- **HTML meta tags**: Some publishers embed opt-out directives in page metadata.

- **Terms of service**: Plain text legal language buried in website terms.

The last option is where things get properly contentious. A [German court ruling](https://www.mofo.com/resources/insights/to-scrape-or-not-to-scrape-first-court-decision-on-the-eu-copyright-exception-for-text-and-data-mining-in-germany) concluded that "machine-readable" should be interpreted as "machine-understandable." The court suggested that natural language terms of service might satisfy the requirement, on the basis that modern NLP-capable crawlers can parse them.

Effectively, if your crawler is smart enough to understand natural language (and if you are building LLMs, arguably it is), then natural language opt-outs are valid. The burden shifts entirely to the AI developer to understand *any* format of reservation, regardless of how it is expressed.

Think about what that actually means. You need an LLM to work out whether you're allowed to train one.

### A Practical Opt-Out Scanner

For fine-tuning pipelines that ingest web content, you need to check for opt-outs before any data enters the training set. Here is a scanner that checks the most common mechanisms:

```python
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List
from urllib.parse import urlparse

import httpx


class OptOutStatus(Enum):
    CLEAR = "clear"        # No reservation found
    RESERVED = "reserved"  # Explicit opt-out detected
    UNKNOWN = "unknown"    # Could not determine


@dataclass
class OptOutResult:
    url: str
    status: OptOutStatus
    signals: List[str] = field(default_factory=list)

    def blocked(self) -> bool:
        return self.status in (OptOutStatus.RESERVED, OptOutStatus.UNKNOWN)


AI_BOT_NAMES = [
    "GPTBot", "CCBot", "Google-Extended",
    "anthropic-ai", "Bytespider", "FacebookBot",
]


class TDMOptOutScanner:
    """Checks a URL for TDM rights reservations before
    content enters a fine-tuning pipeline.

    Scans robots.txt, ai.txt, HTTP headers, and HTML meta tags.
    Fails closed: if we cannot determine opt-out status, the
    content is blocked from training."""

    def __init__(self, bot_name: str = "CustomFineTuneBot"):
        self.bot_name = bot_name
        self.client = httpx.Client(timeout=10, follow_redirects=True)

    def check(self, url: str) -> OptOutResult:
        result = OptOutResult(url=url, status=OptOutStatus.CLEAR)
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # Layer 1: robots.txt
        self._check_robots(base, result)

        # Layer 2: ai.txt
        self._check_ai_txt(base, result)

        # Layer 3: HTTP headers on the target page
        self._check_http_headers(url, result)

        # Determine final status
        if result.signals:
            result.status = OptOutStatus.RESERVED

        return result

    def _check_robots(self, base_url: str, result: OptOutResult):
        try:
            resp = self.client.get(f"{base_url}/robots.txt")
            if resp.status_code != 200:
                return

            content = resp.text.lower()

            # Check for blocks on known AI bots
            for bot in AI_BOT_NAMES + [self.bot_name]:
                pattern = rf"user-agent:\s*{re.escape(bot.lower())}"
                if re.search(pattern, content):
                    # Check if followed by Disallow: /
                    section = content[content.index(bot.lower()):]
                    if "disallow: /" in section.split("user-agent")[0]:
                        result.signals.append(
                            f"robots.txt blocks {bot}"
                        )

        except httpx.HTTPError:
            pass  # robots.txt not available; not an opt-out signal

    def _check_ai_txt(self, base_url: str, result: OptOutResult):
        try:
            resp = self.client.get(f"{base_url}/ai.txt")
            if resp.status_code != 200:
                return

            content = resp.text.lower()
            if "disallow" in content or "no" in content:
                result.signals.append("ai.txt contains restriction")

        except httpx.HTTPError:
            pass

    def _check_http_headers(self, url: str, result: OptOutResult):
        try:
            resp = self.client.head(url)

            # TDMRep protocol: X-Robots-Tag or custom TDM headers
            tdm_header = resp.headers.get("tdm-reservation", "")
            if tdm_header.strip() == "1":
                result.signals.append("TDM-Reservation header set")

            x_robots = resp.headers.get("x-robots-tag", "")
            if "noai" in x_robots.lower() or "noimageai" in x_robots.lower():
                result.signals.append(f"X-Robots-Tag: {x_robots}")

        except httpx.HTTPError:
            pass


# Usage in a fine-tuning data pipeline
scanner = TDMOptOutScanner(bot_name="AcmeFineTuneBot")

urls_to_check = [
    "https://example-publisher.com/article/123",
    "https://example-news.co.uk/story/456",
]

for url in urls_to_check:
    result = scanner.check(url)
    if result.blocked():
        print(f"BLOCKED: {url}")
        print(f"  Signals: {result.signals}")
    else:
        print(f"CLEAR: {url}")
```

The scanner fails closed. If it detects any reservation signal, the content is blocked from the training set. If it cannot determine the status (network errors, ambiguous signals), it blocks by default. This is the conservative approach, and for cross-border compliance, conservative is correct.

What this scanner does not do is parse natural language terms of service. That is a deliberate choice. The German court ruling may have opened that door, but building NLP-based legal interpretation into your data pipeline introduces a whole new category of risk. If your system misinterprets a term and ingests data it should not have, you have a copyright problem *and* a technical credibility problem. Better to flag ambiguous cases for human review.

---

## When Fine-Tuning Makes You a Provider

Under the [EU AI Act (Regulation 2024/1689)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj), fine-tuning an existing model can change your legal status. If the modification is "substantial," the modifier becomes the "provider" of a new general-purpose AI (GPAI) model, inheriting the full set of provider obligations: technical documentation, training content summaries, copyright compliance policies, and downstream integrator support.

The [AI Office's guidelines](https://digital-strategy.ec.europa.eu/en/library/commission-publishes-guidelines-definition-ai-system) suggest a compute-based threshold. If your fine-tuning requires more than one-third of the floating-point operations (FLOPs) used to train the original model, the modification is presumed substantial.

For most practical fine-tuning work, this threshold matters. Consider the maths:

- **LoRA or QLoRA fine-tuning** on a 70B model typically uses a tiny fraction of the original training compute. You are updating a small set of adapter weights, not the full model. This almost certainly falls below the one-third threshold. You remain a "deployer," not a provider.

- **Full parameter fine-tuning** on a large model, especially with multiple epochs over a substantial dataset, could approach or exceed the threshold. If you are doing extensive continued pre-training (sometimes called "domain-adaptive pre-training"), you are likely crossing the line.

The practical implication: know your FLOPs. If you are anywhere near the threshold, you need to prepare the full suite of EU AI Act documentation. That includes the [training content summary template](https://digital-strategy.ec.europa.eu/en/library/template-sufficiently-detailed-summary-training-content) published by the AI Office in July 2025, which requires narrative disclosure of data sources, the top 10% of domains scraped, and the methods used to respect copyright opt-outs.

This documentation requirement covers all stages of training, including fine-tuning. If you fine-tune a model that was originally trained by someone else, you are responsible for documenting *your* fine-tuning data, not just inheriting the upstream provider's summary.

---

## Why You Can't Delete Data from a Trained Model

The right to erasure under [Article 17 of the GDPR](https://gdpr-info.eu/art-17-gdpr/) requires controllers to delete personal data "without undue delay" when requested. In a traditional database, you find the record and delete it. In a trained neural network, the data has been blended into billions of parameters. Researchers have compared it to trying to retrieve a specific strawberry from a smoothie. Once the weights have been updated, the influence of any single data point is diffused throughout the model.

If someone whose data appeared in your fine-tuning set requests erasure, what does compliance actually look like?

### The Spectrum of Responses

The [EDPB's Support Pool of Experts](https://www.edpb.europa.eu/our-work-tools/our-documents/other/ai-complex-algorithms-and-effective-data-protection_en) has mapped out the options, from the most rigorous to the most pragmatic:

**Full retraining.** Delete the data from the training set and retrain the model from scratch. This is the gold standard for compliance. It is also ruinously expensive. For large models, a single training run can cost millions of euros in compute. Retraining every time someone exercises their Article 17 rights is not viable for anyone.

**SISA (Sharded, Isolated, Sliced, Aggregated).** Split the training data into independent shards. Train separate sub-models on each shard. Aggregate them for inference. When an erasure request arrives, identify which shard contained the data, and retrain only that shard. The rest of the model is untouched. This is currently considered the most viable approach for deep neural networks that need to support deletion.

**Influence functions.** Use mathematical techniques (second-order derivatives) to estimate how much a specific data point affected the model's weights, then "undo" those updates. Faster than retraining, but less precise. The maths is complex and the guarantees are weaker.

**Output filtering.** Intercept queries or responses to suppress the generation of specific data. This provides immediate protection but does not remove the data's influence from the model parameters. Most regulators would not consider this "erasure" in a strict sense.

### Designing for Deletion at Training Time

Erasure compliance needs to be designed in at training time. If you train a model as a single monolithic process, you have no escape hatch when an erasure request arrives.

SISA gives you that escape hatch. Here is a simplified version of a sharded training data registry that tracks which data points sit in which shard, supports erasure lookups, and identifies which shards need retraining:

```python
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class LicenceStatus(Enum):
    LICENSED = "licensed"
    TDM_CLEAR = "tdm_clear"    # EU Art 4, no opt-out detected
    PENDING = "pending_review"
    REJECTED = "rejected"


@dataclass
class DataPoint:
    id: str
    source_url: str
    content_hash: str
    licence: LicenceStatus
    contains_pii: bool
    pii_subject_ids: List[str] = field(default_factory=list)
    ingested_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


@dataclass
class Shard:
    shard_id: str
    data_points: Dict[str, DataPoint] = field(default_factory=dict)
    last_trained: Optional[str] = None
    needs_retrain: bool = False

    def add(self, dp: DataPoint):
        self.data_points[dp.id] = dp

    def remove(self, dp_id: str) -> bool:
        if dp_id in self.data_points:
            del self.data_points[dp_id]
            self.needs_retrain = True
            return True
        return False

    def subject_data_points(self, subject_id: str) -> List[str]:
        return [
            dp_id for dp_id, dp in self.data_points.items()
            if subject_id in dp.pii_subject_ids
        ]


class ShardedTrainingRegistry:
    """Manages fine-tuning data across independent shards.

    Supports GDPR Article 17 erasure by tracking which data
    subjects appear in which shards. When erasure is requested,
    only the affected shards are marked for retraining."""

    def __init__(self, num_shards: int = 8):
        self.shards: Dict[str, Shard] = {
            f"shard_{i}": Shard(shard_id=f"shard_{i}")
            for i in range(num_shards)
        }
        self.num_shards = num_shards

    def _assign_shard(self, dp_id: str) -> str:
        """Deterministic shard assignment via consistent hashing."""
        h = int(hashlib.md5(dp_id.encode()).hexdigest(), 16)
        idx = h % self.num_shards
        return f"shard_{idx}"

    def ingest(self, dp: DataPoint) -> Optional[str]:
        """Add a data point to the registry. Returns the shard ID,
        or None if the data point is blocked by policy."""

        # Policy gate: reject unlicensed or unreviewed data
        if dp.licence in (LicenceStatus.REJECTED, LicenceStatus.PENDING):
            print(f"BLOCKED: {dp.id} ({dp.licence.value})")
            return None

        shard_id = self._assign_shard(dp.id)
        self.shards[shard_id].add(dp)
        return shard_id

    def request_erasure(self, subject_id: str) -> List[str]:
        """Process an Article 17 erasure request.

        Finds all data points associated with the subject,
        removes them, and returns the list of shards that
        need retraining."""

        affected_shards: List[str] = []

        for shard_id, shard in self.shards.items():
            dp_ids = shard.subject_data_points(subject_id)
            for dp_id in dp_ids:
                shard.remove(dp_id)
                print(f"  Erased {dp_id} from {shard_id}")

            if shard.needs_retrain and shard_id not in affected_shards:
                affected_shards.append(shard_id)

        if affected_shards:
            print(
                f"Erasure complete for subject {subject_id}. "
                f"Shards needing retrain: {affected_shards}"
            )
        else:
            print(f"No data found for subject {subject_id}")

        return affected_shards

    def compliance_summary(self) -> Dict:
        """Generate a summary for audit purposes."""
        return {
            shard_id: {
                "data_points": len(shard.data_points),
                "needs_retrain": shard.needs_retrain,
                "last_trained": shard.last_trained,
                "pii_subjects": len({
                    sid
                    for dp in shard.data_points.values()
                    for sid in dp.pii_subject_ids
                }),
            }
            for shard_id, shard in self.shards.items()
        }


# Usage

registry = ShardedTrainingRegistry(num_shards=4)

# Ingest training data with provenance tracking
registry.ingest(DataPoint(
    id="doc_001",
    source_url="https://licensed-corpus.eu/article/1",
    content_hash="a1b2c3",
    licence=LicenceStatus.LICENSED,
    contains_pii=True,
    pii_subject_ids=["subject_42"],
))

registry.ingest(DataPoint(
    id="doc_002",
    source_url="https://news-site.eu/story/5",
    content_hash="d4e5f6",
    licence=LicenceStatus.TDM_CLEAR,
    contains_pii=False,
))

# This one gets blocked: no licence
registry.ingest(DataPoint(
    id="doc_003",
    source_url="https://paywalled-site.co.uk/premium/7",
    content_hash="g7h8i9",
    licence=LicenceStatus.REJECTED,
    contains_pii=False,
))

# Subject 42 exercises their right to erasure
affected = registry.request_erasure("subject_42")

# Audit output
print(json.dumps(registry.compliance_summary(), indent=2))
```

The registry enforces two things. First, it blocks data that has not been properly licensed or cleared under TDM rules. Second, it tracks which data subjects appear in which shards, so that when an erasure request arrives, the blast radius is limited. You retrain one shard, not the entire model.

In a production system, the sharding strategy would be more sophisticated. You would want to balance shard sizes, avoid clustering high-PII data in a single shard (which would make that shard expensive to retrain frequently), and integrate with your model training pipeline so that "needs_retrain" flags trigger actual retraining jobs. The principle is the same: modularity at training time buys you flexibility at compliance time.

---

## Legitimate Interest Is Not a Free Pass

If your fine-tuning data contains personal data (and if it came from the web, it almost certainly does), you need a lawful basis under the GDPR. Consent is a non-starter for large-scale training. You cannot meaningfully get informed, specific consent from every person whose data appears in a web-scraped corpus.

That leaves [legitimate interest (Article 6(1)(f))](https://gdpr-info.eu/art-6-gdpr/) as the practical option. Both the UK's [ICO](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/legitimate-interests/) and the EU's [EDPB (Opinion 28/2024)](https://www.edpb.europa.eu/our-work-tools/our-documents/opinion-board-art-64/opinion-282024-certain-data-protection-aspects_en) accept this as a viable basis for AI training. But neither treats it as a blank cheque.

The legitimate interest assessment has three parts, and both regulators are increasingly specific about what they expect:

**The purpose test.** You need a specific, documented purpose. "General model improvement" or "advancing AI capabilities" will not pass. Something like "fine-tuning for medical document summarisation in cardiology" will. The purpose needs to be concrete enough that you can later evaluate whether it was achieved.

**The necessity test.** Could you reach the same goal with less personal data? If synthetic data, anonymised datasets, or licensed collections would work, you need to explain why you are not using them. The ICO has been explicit: developers must demonstrate why licensed alternatives were not feasible.

**The balancing test.** Your interest must outweigh the rights and reasonable expectations of the people in the data. This is where the UK and EU diverge in an interesting way. The EDPB focuses on traditional privacy harms: discrimination, re-identification, surveillance. The ICO, in its [December 2024 generative AI consultation outcomes](https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/2024/12/ico-publishes-updated-approach-to-generative-ai-and-data-protection/), added a broader category. If your AI model displaces human workers (fashion models, illustrators, writers), the economic harm to those individuals should factor into the balancing test.

A data protection regulator is now asking you to consider whether your model puts people out of work. Whether you think that is appropriate or overreach, it is the stated position of the UK's regulator and it needs to be reflected in your legitimate interest assessment.

| | EU (EDPB Opinion 28/2024) | UK (ICO GenAI Outcomes, Dec 2024) |
| --- | --- | --- |
| **Purpose definition** | Must be "clearly and precisely articulated" and non-speculative | Rejects broad purposes like "innovation"; requires specific, documented use cases |
| **Necessity standard** | High threshold; developers must justify why personal data is used over synthetic data | Requires proof that alternative data sources (e.g. licensed sets) were not feasible |
| **Balancing and harm** | Focuses on privacy, discrimination, and potential for re-identification | Adopts a "broad harm" approach, including economic harms like job displacement |
| **Transparency role** | Crucial for "reasonable expectations"; mere privacy notices may not suffice | Demands "meaningful" transparency; developers must test if users actually understand the notice |

---

## Putting It Together

The fine-tuning pipeline for cross-border compliance has five stages, each with its own legal checkpoint:

1. **Source and licence.** Before any data enters the pipeline, verify its copyright status. For licensed data, record the licence terms. For web-scraped data, run the opt-out scanner. For UK-destined models, treat all copyrighted material as requiring a licence.

2. **Classify and document.** Scan for personal data. Record which data subjects appear in which records. Assign each data point to a shard. This is where the SISA architecture begins.

3. **Assess legitimate interest.** Document the specific purpose, the necessity analysis, and the balancing test. Include economic impact considerations for the UK market. This is a legal document, but it needs technical inputs: what data are you using, why, and what alternatives did you evaluate.

4. **Train in shards.** Run fine-tuning across independent shards. Log the compute used (you need this to determine whether you have crossed the one-third FLOP threshold under the AI Act). Maintain an immutable record of which data went into which shard and when.

5. **Publish the summary.** If you are operating in the EU market and your modification is substantial, generate the training content summary using the [AI Office template](https://digital-strategy.ec.europa.eu/en/library/template-sufficiently-detailed-summary-training-content). This must cover your fine-tuning data specifically, not just inherit the upstream model's documentation.

None of this is optional for serious cross-border deployment. The EU AI Act obligations for GPAI providers are enforceable from August 2025. The UK's copyright position will crystallise by mid-2026. Building the pipeline now, with these constraints baked in, is cheaper than retrofitting compliance after the fact.

---

## References

### EU Legislation

- **[DSM Directive (Directive (EU) 2019/790)](https://eur-lex.europa.eu/eli/dir/2019/790/oj)**
  - Article 3: TDM exception for research organisations (mandatory, no opt-out)
  - Article 4: TDM exception for any purpose (opt-out via machine-readable means)

- **[EU AI Act (Regulation (EU) 2024/1689)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)**
  - GPAI provider obligations: documentation, training content summaries, copyright compliance
  - Substantial modification threshold: one-third of original training FLOPs

- **[GDPR (Regulation (EU) 2016/679)](https://eur-lex.europa.eu/eli/reg/2016/679/oj)**
  - Article 6(1)(f): Legitimate interests as lawful basis
  - Article 17: Right to erasure

- **[EDPB Opinion 28/2024](https://www.edpb.europa.eu/our-work-tools/our-documents/opinion-board-art-64/opinion-282024-certain-data-protection-aspects_en)**: Data protection aspects of personal data processing in AI models

- **[AI Office Training Content Summary Template (July 2025)](https://digital-strategy.ec.europa.eu/en/library/template-sufficiently-detailed-summary-training-content)**: Mandatory disclosure format for GPAI providers

- **[TDMRep W3C Community Group](https://www.w3.org/community/tdmrep/)**: Proposed technical standard for TDM rights reservation

### UK Legislation

- **[Copyright, Designs and Patents Act 1988, Section 29A](https://www.legislation.gov.uk/ukpga/1988/48/section/29A)**: TDM exception for non-commercial research only

- **[Data (Use and Access) Act 2025](https://www.legislation.gov.uk/ukpga/2025/1/contents/enacted)**
  - Section 135: Economic impact assessment of copyright policy options (due March 2026)
  - Section 136: Report on use of copyright works in AI development (due March 2026)

- **[UK Copyright and AI Consultation (December 2024 to February 2025)](https://www.gov.uk/government/consultations/copyright-and-artificial-intelligence)**: Four policy options; Option 3 (opt-out model) was the government's preferred path

- **[ICO Generative AI Consultation Outcomes (December 2024)](https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/2024/12/ico-publishes-updated-approach-to-generative-ai-and-data-protection/)**: Legitimate interest guidance, broad harm approach in balancing test

### Case Law and Technical Standards

- **[KNHG v LAION (Germany)](https://www.mofo.com/resources/insights/to-scrape-or-not-to-scrape-first-court-decision-on-the-eu-copyright-exception-for-text-and-data-mining-in-germany)**: First EU court decision on TDM exception; interpreted "machine-readable" as "machine-understandable"

- **[EDPB Support Pool of Experts Report on Machine Unlearning](https://www.edpb.europa.eu/our-work-tools/our-documents/other/ai-complex-algorithms-and-effective-data-protection_en)**: Technical analysis of SISA, influence functions, and verification methods for data erasure in AI models
