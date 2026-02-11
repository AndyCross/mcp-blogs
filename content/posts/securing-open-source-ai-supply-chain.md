+++
title = "Securing the Open Source AI Supply Chain"
date = "2026-02-13"
draft = false
tags = ["ai", "europe", "sovereignty", "security", "supply-chain"]
series = ["european-ai-sovereignty"]
+++

This is the fourth post in a series on European AI sovereignty. I have covered [why jurisdiction matters](/posts/european-ai-sovereignty/), [how to handle UK-EU regulatory divergence in code](/posts/compliance-as-code-two-europes/), and [a practical guide to the sovereign inference stack](/posts/sovereign-inference-stack/). Those posts treated the open-source AI toolchain as a given. PyTorch, Llama, vLLM, Hugging Face. Just pick your models and deploy.

This post asks a harder question: what happens when the toolchain itself is the threat?

Open-source frameworks like PyTorch and open-weight models like Llama have democratised access to frontier-level AI. That is genuinely remarkable. But they have also introduced a web of dependencies that is susceptible to supply chain attacks, adversarial manipulation, and geopolitical pressure. The [NCSC](https://www.ncsc.gov.uk/blog-post/machine-learning-security-principles-updated), [ENISA](https://www.enisa.europa.eu/topics/cyber-threats/threat-landscape), and the [Australian Cyber Security Centre](https://www.cyber.gov.au/business-government/secure-design/artificial-intelligence/artificial-intelligence-and-machine-learning-supply-chain-risks-and-mitigations) have all published guidance on this. The supply chain problem is not a glitch to be patched. It is a structural vulnerability that touches critical infrastructure, from energy grids to healthcare systems.

If you are building a sovereign AI platform on open-source foundations, you need to understand where the risks actually sit.

---

## What XZ Utils Teaches Us About ML Security

The security community was properly shaken by the [XZ Utils backdoor](https://en.wikipedia.org/wiki/XZ_Utils_backdoor) discovery. A malicious actor spent years building trust within the open-source community to eventually insert a backdoor into a foundational compression library used by most Linux distributions. It was a multi-year social engineering attack on a piece of infrastructure that almost nobody was paying attention to.

The ML supply chain has the same structural properties, only the attack surfaces are broader. In traditional software, vulnerabilities tend to live in logic flaws. In ML systems, there are additional layers to worry about: the serialisation layer, the weight-optimisation layer, and the hardware-interface layer. Your dependencies are not just code. They include data artefacts and hardware-specific binary kernels.

The modern ML stack, built predominantly on Python and PyTorch, relies on thousands of sub-dependencies. The discovery of [CVE-2025-32434](https://medium.com/@neorusiwork/pytorch-security-crisis-how-a-critical-vulnerability-threatens-the-ai-ecosystem-and-what-to-do-2d3c74d11c26) (a critical vulnerability in PyTorch) made this concrete. Even the `weights_only=True` parameter in `torch.load`, which was supposed to prevent arbitrary code execution, could be bypassed through carefully crafted model files. A common zip archive became an attack vector.

The lesson for sovereign platforms is straightforward: shared responsibility in open-source communities often becomes a tragedy of the commons. Everyone assumes someone else is verifying the code. [Python's packaging system](https://arxiv.org/html/2512.23385v1) compounds this, because attackers can embed malware in commonly used packages that get pulled automatically during development workflows.

This demands a shift from "trust by default" to something more like verifiable autonomy. Every component of the pipeline needs to be accounted for through automated Software Bills of Materials (SBOMs), strict dependency pinning, and reproducible build environments. Nothing revolutionary there, but the ML world has been remarkably slow to adopt these practices compared to traditional software engineering.

---

## Threat Modelling the Machine Learning Pipeline

Securing the UK and EU AI supply chain requires understanding how ML threat vectors differ from traditional IT security. Attackers targeting ML pipelines do not just want to crash systems. They want to subvert model logic, exfiltrate training data, or establish persistent backdoors that survive model updates.

| Threat Vector | How It Works | What It Targets | What It Means |
| --- | --- | --- | --- |
| **Poisoned Weights** | Embedding hidden triggers during training or fine-tuning. | Model checkpoints (.bin, .pt, .safetensors) | Model behaves normally on standard inputs but executes malicious logic when triggered. |
| **Malicious Kernels** | Injecting unauthorised logic into low-level C++ or CUDA kernels for tensor operations. | Hardware abstraction layer (CUDA, ROCm, OneAPI) | Persistent, low-level system access that evades Python-based security scans. |
| **[Namespace Hijacking](https://unit42.paloaltonetworks.com/model-namespace-reuse/)** | Re-registering deleted or abandoned author names on registries like Hugging Face. | Model repositories and author namespaces | Users download malicious versions of models they trust. |
| **Pickle Deserialisation** | Exploiting Python's insecure serialisation format to execute arbitrary code at load time. | Model loading functions (`torch.load`) | Remote code execution on inference servers or developer machines. |
| **Prompt Injection** | Using data inputs to override model instructions or exfiltrate data. | Inference APIs and agentic workflows | Unauthorised data disclosure or manipulation of downstream actions. |
| **Hallucinated Dependencies** | Tricking LLMs into suggesting non-existent packages that the attacker then registers on PyPI. | Development environments (pip, conda) | Initial access through typosquatting and hallucination-driven dependency pulls. |

The technical fallout from these attacks cascades. A compromised ML component can silently alter codebases, introduce SSH backdoors, and [hijack internal APIs](https://www.datadoghq.com/blog/detect-abuse-ai-supply-chains/). Both [NCSC](https://www.ncsc.gov.uk/files/Guidelines-for-secure-AI-system-development.pdf) and [ENISA](https://www.enisa.europa.eu/topics/cyber-threats/threat-landscape) have warned that treating AI vulnerabilities like traditional software bugs leads to large-scale breaches. Prompt injection is not SQL injection. It requires different mitigations and a deeper understanding of emergent behaviours.

---

## How NCSC and ENISA Are Responding

The UK and EU have both published frameworks for ML security. They share a "security by design" philosophy but differ in tactical approach.

### NCSC Principles for Secure Machine Learning

The NCSC's ["Principles for the security of machine learning"](https://www.ncsc.gov.uk/collection/machine-learning-principles/secure-development/secure-supply-chain), originally published in 2022 and updated in 2024, cover the full lifecycle of an AI system. The framework recognises that weaknesses in hardware, software, and data pipelines can all be exploited. The NCSC's core position is that ML security is inherently harder than normal cybersecurity.

The framework covers four areas:

1. **Secure Design.** Staff awareness of adversarial machine learning threats. Senior management must understand the trade-offs between performance and security.
2. **Secure Development.** Supply chain security, documentation, and technical debt management. The NCSC explicitly recommends a Machine Learning Bill of Materials (ML-BOM) to catalogue all open-source and third-party components.
3. **Secure Deployment.** Protecting infrastructure from compromise and developing incident management processes trained specifically for AI anomalies.
4. **Secure Operation.** Managing updates, logging, and information sharing to keep the system resilient against evolving threats.

The NCSC also [stresses](https://www.dni.gov/files/NCSC/documents/supplychain/NCSC-Managing-Supply-Chain-Risk-to-Machine-Learning.pdf) that data is a critical part of the supply chain. Understanding the provenance of training data, and whether an attacker had the opportunity to subvert it, is as important as code review.

### ENISA's Multilayer Framework

ENISA's [Framework for AI Cybersecurity Practices (FAICP)](https://complexdiscovery.com/good-cybersecurity-practices-for-ai-a-multilayer-framework-enisa/) takes a different approach. It provides a step-by-step methodology for national competent authorities and AI stakeholders, divided into three layers:

- **Layer I, Cybersecurity Foundations.** AI systems run on ICT infrastructure that must first be secured using existing practices and standards like ISO/IEC 27001. Get the basics right before worrying about AI-specific threats.
- **Layer II, AI-Specific Cybersecurity.** This addresses the additional challenges from the dynamic, socio-technical nature of AI: model inversion, data poisoning, and the rest of the ML-specific threat landscape.
- **Layer III, Sector-Specific Cybersecurity.** The risk profile of an AI system changes depending on what it does. Medical imaging has a different threat model from electricity grid forecasting. This layer adds tailored controls for specific domains.

ENISA's guidance is shaped by the [NIS2 Directive](https://www.enisa.europa.eu/topics/cybersecurity-policy/nis-directive-new), which aims for a high common level of cybersecurity across the EU. One statistic from ENISA's [supply chain analysis](https://www.enisa.europa.eu/sites/default/files/publications/Good%20Practices%20for%20Supply%20Chain%20Cybersecurity.pdf) stands out: in 66% of analysed supply chain attacks, suppliers did not know or failed to disclose how they were compromised. The EU AI Act is, in part, an attempt to close that transparency gap.

---

## Inside the PyTorch Project

PyTorch is the primary framework for both research and production AI in the UK and EU. Its internal health is a proxy for the security of the wider ML supply chain. The [PyTorch GitHub pulse](https://gitlights.com/pytorch/github-commits) reveals a project of immense scale and rapid evolution, but also one with a concentrated core of contributors.

### Development Velocity

PyTorch's development pace is driven by the competitive demands of the generative AI era. By early 2025, the project was averaging [31.2 commits per day](https://buttondown.com/weekly-project-news/archive/weekly-github-report-for-pytorch-january-25-2026-9738/). In a typical month, the organisation adds over 1.25 million lines and deletes nearly 800,000. The net gain points to continuous feature expansion rather than maintenance.

| Metric (2025 Est.) | Value / Trend | What It Means |
| --- | --- | --- |
| **Commit Frequency** | 31.2 per day | High innovation rate but challenging for manual security audits. |
| **Average Lines per Commit** | 125.9 additions / 70.6 deletions | Focus on new features like `torch.compile` and AOTInductor. |
| **Total Committers** | >2,000 | Broad community but Bus Factor issues in core kernels. |
| **Repository Concentration** | 62% of activity in the main `pytorch` repo | A centralised point of failure for the global ML supply chain. |
| **Update Cadence** | Major releases quarterly; point releases monthly | Critical for security patching but creates update fatigue in regulated sectors. |

The [PyTorch 2.6 release](https://arxiv.org/html/2304.14226) in early 2025 introduced `torch.compile` support for Python 3.13 and improved AOTInductor compatibility, producing a 43% speedup in end-to-end latency benchmarks for certain GEMM operations. These performance gains rely on deeper integration with low-level hardware features. Good for speed, less so for auditability.

### Contributor Concentration and Governance

Despite over 2,000 contributors, the [Bus Factor](https://pytorch.org/blog/pytorch-contributor-awardees-2025/) is a real concern. The 2025 PyTorch Contributor Awards highlight a core group of individuals, many affiliated with Meta, NVIDIA, and a handful of other large tech companies, who manage the most critical subsystems. Access to trunk is restricted to repository administrators through a merge bot and protected branches.

PyTorch also requires workflow run approval for pull requests from non-members, partly to prevent cryptocurrency miners from abusing the GPU CI infrastructure. This protects the CI/CD pipeline, but it also bottlenecks code review through a small number of authorised reviewers. A "sleeper" contributor who had built sufficient social capital would have a path to bypass scrutiny. This is exactly what happened with XZ Utils.

---

## CUDA and the Proprietary Black Box

The most significant bottleneck in UK/EU sovereign AI is the reliance on NVIDIA's CUDA software stack. CUDA is not just a driver. It is a complete, proprietary software stack that has created deep technological lock-in since 2006.

### Why CUDA Dominance Matters

PyTorch provides a clean Pythonic abstraction for developers. Beneath that abstraction, the framework relies on pre-written code libraries and kernels finely tuned for NVIDIA hardware. Companies training large models are often running code they cannot fully audit or modify. NVIDIA's engineers have spent years ensuring that PyTorch runs optimally on their chips, creating a software moat that is difficult for competitors to cross.

For sovereign platforms, the risk is two-fold:

1. **Security opacity.** Proprietary binaries in the CUDA stack cannot be easily scanned for latent vulnerabilities or backdoors.
2. **Economic dependency.** The gap between the PyTorch frameworks most developers use and the internal frameworks of competitors (like Google's Jax) means switching away from NVIDIA requires substantial extra engineering effort.

### TorchTPU and the Open Alternatives

There is movement here. [Google and Meta have partnered](https://www.thehindu.com/sci-tech/technology/google-works-to-erode-nvidias-software-advantage-with-metas-help/article70409936.ece) on the "TorchTPU" initiative to make Google's Tensor Processing Units fully compatible with PyTorch. The goal is to lower switching costs by re-engineering the software layer that currently anchors the AI world to CUDA.

Research from Stanford has also shown that [LLMs can now generate CUDA kernels](https://the-decoder.com/ai-generated-cuda-kernels-outperform-pytorch-in-several-gpu-heavy-machine-learning-benchmarks/) that sometimes outperform PyTorch's own built-in routines. Rather interesting from a performance perspective, but it introduces a new category of "AI-generated code" into the supply chain. Verifying machine-written kernels is harder than verifying human-written ones.

---

## European Alternatives and Sovereign Inference

The drive for digital sovereignty has produced the ["EuroStack" vision](https://www.bertelsmann-stiftung.de/fileadmin/files/user_upload/EuroStack__2025_final__1_.pdf), a framework intended to protect data, build independent public infrastructure, and reduce dependence on US platforms. In practice, [European alternatives to NVIDIA](https://lab.abilian.com/Tech/Tech%20%26%20Society/Europan%20Alternatives%20to%20Nvidia/) fall into three categories:

1. **Niche players.** Companies like STMicroelectronics and Kalray provide specialised chips for edge AI or automotive applications. This is a survival strategy. It cedes the strategic data centre market to US firms.
2. **Long-term public R&D.** The European Processor Initiative (EPI) and SiPearl aim to develop homegrown processors based on open architectures like RISC-V. Strategically necessary, but these are high-risk bets that must compete with the rapid hardware development cycle in the US.
3. **Underfunded challengers.** Startups with the technology but not the capital to compete with NVIDIA or the US hyperscalers.

None of these are a short-term answer to the CUDA problem. So what do you do now, today, if you are building a sovereign platform on NVIDIA hardware you cannot fully audit?

The practical interim strategy is to isolate the CUDA dependency as aggressively as possible. Containerise your training and inference workloads so the CUDA runtime is a pinned, versioned artefact rather than something installed on bare metal. Use PyTorch's device-agnostic APIs (`torch.device`, the `accelerate` library) rather than writing CUDA-specific code directly. Target the ONNX Runtime or TorchScript export paths where you can, so your models are not permanently welded to a single backend. And build your CI/CD pipeline so that swapping the hardware abstraction layer is a configuration change, not a rewrite.

This will not give you sovereignty over the CUDA binaries themselves. But it will give you a credible exit path when the European alternatives mature, and it limits the blast radius if a CUDA-layer vulnerability is discovered.

### Mistral and Open Weights

[Mistral AI](https://docs.mistral.ai/) has positioned itself as the European leader in generative AI by providing open and portable models. Unlike proprietary offerings from OpenAI or Google, Mistral's [open-weight models](https://trust.mistral.ai/) allow European enterprises to host intelligence in-region, maintaining data sovereignty while accessing capable multimodal models. The releases of Mistral Large 3 and Devstral 2 provide high-performance alternatives for software engineering and general-purpose reasoning that integrate fully into sovereign cloud environments.

I covered this in more detail in the [sovereign inference stack post](/posts/sovereign-inference-stack/).

### vLLM and Modular Inference

In the inference space, [vLLM](https://github.com/vllm-project/vllm) has emerged as the dominant open-source engine, with [over 2,000 contributors](https://www.reddit.com/r/LocalLLaMA/comments/1q4bhtm/vllm_reaches_2000_contributors/). For European developers seeking to optimise on non-NVIDIA hardware, the [vLLM "Metal" plugin](https://medium.com/@michael.hannecke/why-sovereign-llm-inference-on-apple-silicon-341fdd7daf60) (led by engineers at Docker) offers a path to run models on Apple Silicon and other integrated architectures.

The shift towards modular inference engines matters for security. Organisations can justify their stack to security reviews through official project designations and governance structures, rather than depending on independent, single-maintainer repositories.

---

## Meta's Llama and the Influence of the Herd

Meta's Llama series has [fundamentally altered the economics of AI](https://markets.financialcontent.com/stocks/article/tokenring-2026-2-5-the-open-source-revolution-how-metas-llama-series-erased-the-proprietary-ai-advantage), eroding the proprietary advantage that closed-model providers once enjoyed. But the strategic influence of Llama comes with complex licensing and technical dependencies.

### From Dense Models to Mixture-of-Experts

The transition from the dense architectures of Llama 3 to the Mixture-of-Experts (MoE) framework of Llama 4 is a significant technical shift. The [flagship "Maverick" model](https://aws.amazon.com/blogs/machine-learning/llama-4-family-of-models-from-meta-are-now-available-in-sagemaker-jumpstart/) uses 400 billion total parameters but only activates 17 billion for any single inference pass. This allows high-quality outputs at lower computational cost.

The MoE architecture works through a gating network `G(x)` that determines which expert `E_i(x)` handles each input:

```
y = Σ(i=1..n) G(x)_i · E_i(x)
```

This sparsity is what allows a model like "Scout" to support context windows of up to 10 million tokens, surpassing many proprietary rivals in long-context retrieval.

### The Open Washing Problem

Meta brands Llama as "Open Source." Both the [Open Source Initiative](https://opensource.org/blog/metas-llama-license-is-still-not-open-source) and the Free Software Foundation disagree. The Llama Community License restricts commercial scale and fields of use, which fails the Open Source Definition. For European users specifically, the licence has at times excluded EU residents from using models without clear explanation.

Despite this, the ["Llama Stack"](https://thealliance.ai/blog/ai-alliance-accelerating-open-source-ai-innovation) (a framework for standardising generative AI application building blocks) has gained traction with major partners including AWS, NVIDIA, and Dell. But reliance on Meta's reference implementation has already produced critical vulnerabilities, including the [ZeroMQ/Pickle RCE (CVE-2024-50050)](https://www.oligo.security/blog/cve-2024-50050-critical-vulnerability-in-meta-llama-llama-stack).

This is where "open washing" has operational consequences. When Meta controls the reference implementation, European users have no say in vulnerability disclosure timelines, no visibility into internal security review processes, and no guarantee that fixes will prioritise their deployment patterns. The CVE-2024-50050 patch came from Meta on Meta's schedule. If you had built your sovereign inference pipeline on Llama Stack, you were waiting for a US company to decide when to fix a remote code execution vulnerability in your production environment. That is a rather uncomfortable position for a platform claiming jurisdictional independence.

---

## What the EU AI Act Demands

The regulatory environment in the EU is moving towards hard law. The [EU AI Act](https://artificialintelligenceact.eu/article/13/) requires high-risk systems to be designed for transparency, with clear instructions and comprehensive technical documentation.

### The ML-BOM Requirement Under Annex IV

[Article 11](https://artificialintelligenceact.eu/article/11/) and [Annex IV](https://artificialintelligenceact.eu/annex/4/) mandate detailed [technical documentation](https://practical-ai-act.eu/latest/conformity/technical-documentation/) before a system can be placed on the market. This documentation must provide authorities with enough information to assess risk. The required elements include:

- **Detailed logic.** The general logic of the AI system, its algorithms, key design choices, and rationale.
- **Resource tracking.** The computational resources used to develop, train, test, and validate the system.
- **Data provenance.** Datasheets describing training methodologies, data acquisition, labelling, and provenance.
- **Cybersecurity measures.** A description of the security controls protecting the model and its pipeline.

### Automating Documentation in Practice

Meeting these requirements without destroying your development velocity requires MLOps automation. Tools for experiment tracking, model registries, and model cards can generate the necessary documentation dynamically.

| Engineering Practice | AI Act Article Mapping | What It Produces |
| --- | --- | --- |
| **Experiment Tracking** | Art. 11(1) & Annex IV(2)(g) | Automated logging of validation data characteristics. |
| **Model Registry** | Art. 11(1) & Annex IV(2)(b) | Capture of model architecture and hyperparameter state. |
| **Model Cards** | Art. 11(1) & Annex IV(1)(a,c,g) | Documentation of intended purpose and versioning. |
| **Data Documentation** | Art. 11(1) & Annex IV(2)(d,e) | Datasheets for provenance and preprocessing. |

---

## Technical Hardening in Practice

Securing the supply chain requires concrete technical controls. The following examples address the most critical areas: identifying dependencies, verifying model authenticity, and ensuring reproducible builds.

### SBOM Generation with Syft and Trivy

Generating a [Software Bill of Materials](https://docs.secure.software/safe/xbom-explainer) is the first step in finding the invisible dependencies in your ML stack.

```bash
# Using Syft to scan a PyTorch development directory
# Syft captures author metadata, licences, and precise package locations
syft . -o cyclonedx-json > sbom.json

# Using Trivy to scan for vulnerabilities in a Python environment
# This flags OS-level and application-level packages
trivy fs --format json --list-all-pkgs --output result.json .

# Filtering for high-risk Python packages in the SBOM
cat sbom.json | jq '.artifacts | select(.language=="python") | {name, version}'
```

### Model Signing and Verification with Sigstore

Model weights are executable code. They should be [signed by the provider and verified by the deployer](https://blog.sigstore.dev/model-transparency-v1.0/). The [OpenSSF Model Signing tool](https://github.com/sigstore/model-transparency) handles this through Sigstore.

```bash
# Signing a model weight file using an OIDC identity (e.g., GitHub Actions)
# This generates an ephemeral certificate and records the event in the Rekor log
model_signing sign /path/to/pytorch_model.bin

# Verification by the deployer
# This checks signature validity and re-calculates file hashes
model_signing verify /path/to/pytorch_model.bin \
  --signature ./model.sig \
  --identity developer@organisation.uk \
  --identity_provider https://github.com/login/oauth
```

### Reproducible Environments and Dependency Locking

The "it works on my machine" problem is a security problem. If your training environment and your production environment resolve different versions of the same package, you have an unaudited gap in your supply chain.

Most teams will start with what they already know. `pip-tools` (with `pip-compile` generating a fully pinned `requirements.txt` from a loose `requirements.in`) is the simplest path. `uv` is a faster, Rust-based alternative that produces the same lockfile format and is gaining traction quickly. Poetry with its `poetry.lock` file achieves the same goal with a different workflow. The point is not which tool you pick. The point is that every dependency, including transitive ones, must be pinned to an exact version and hash.

For teams that need stronger guarantees (particularly around CUDA and cuDNN versions, which live outside Python's packaging world), [Nix](https://discourse.nixos.org/t/how-to-properly-setup-an-environment-with-pytorch/69711) provides full-stack reproducibility. A Nix flake pins everything from the Python interpreter to the GPU driver:

```nix
# A basic Nix flake for a reproducible PyTorch-CUDA environment
{
  description = "Secure ML Development Shell";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
  outputs = { self, nixpkgs }: {
    devShells.x86_64-linux.default = let
      pkgs = import nixpkgs {
        system = "x86_64-linux";
        config.allowUnfree = true; # Required for CUDA
      };
    in pkgs.mkShell {
      buildInputs = [
        pkgs.python311
        pkgs.python311Packages.torch
        pkgs.cudatoolkit
        pkgs.cudnn
      ];
      shellHook = "export CUDA_PATH=${pkgs.cudatoolkit}";
    };
  };
}
```

Nix is admittedly a steeper learning curve than `pip-tools` or `uv`. But if your threat model includes supply chain attacks on native libraries (and if you are reading this post, it should), Nix is the only tool that locks the full stack rather than just the Python layer.

---

## A Practical Checklist for Sovereign AI Platforms

For UK and EU organisations building on open-source foundations, here is a governance and technical checklist for supply chain resilience.

### Strategic Governance

- **Establish a RACI matrix.** Define who is responsible for managing supply chain risks, who is accountable, and who must be kept informed.
- **Identify your critical assets.** Prioritise the security of your most important models and datasets.
- **Tier your suppliers by risk.** Categorise suppliers based on criticality and security posture. Include specific contractual clauses for security compliance.
- **Align with FAICP Layer I.** Ensure the underlying ICT infrastructure follows [ISO/IEC 27001](https://www.iso.org/standard/27001) or equivalent standards.

### Supply Chain and Development

- **Automate SBOM generation.** Integrate [Syft](https://anchore.com/blog/python-sbom-generation/) or [Trivy](https://trivy.dev/docs/latest/supply-chain/sbom/) into CI/CD pipelines to generate an SBOM for every build.
- **Pin and audit dependencies.** Use `pip-audit` or `nix` to ensure all dependencies are pinned and scanned for known CVEs.
- **Verify model provenance.** For every third-party model, document who trained it, what data was used, and who had access.
- **Sandbox untrusted inference.** Never run `torch.load` on untrusted models outside of a sandboxed environment with limited permissions.

### Operation and Maintenance

- **Monitor for ML-specific attacks.** Implement logging that tracks model queries and inputs for signs of prompt injection or data exfiltration.
- **Train responders for AI incidents.** Ensure your incident response team can handle AI-specific scenarios like model poisoning or kernel backdoors.
- **Maintain offline backups.** Store critical model weights and training code in offline, encrypted backups.
- **Patch aggressively.** Aim to address critical vulnerabilities in less than one month.

---

## Where This Leaves Us

The supply chain problem in UK/EU AI is a tension between the speed of innovation and the necessity of control. Open-source frameworks like PyTorch and open-weight models like Llama provide immense value, but they create a hidden debt of risk.

The XZ Utils attack was a wake-up call for traditional open-source infrastructure. The ML supply chain has the same structural vulnerabilities, with additional layers of opacity in model weights, hardware kernels, and data pipelines.

Managing this requires proper technical controls (SBOMs, model signing, reproducible builds, dependency pinning), regulatory compliance through the EU AI Act and NCSC/ENISA frameworks (automated wherever possible so it does not strangle development), and investment in European alternatives like Mistral, EPI, and RISC-V that reduce the surface area of foreign dependency.

None of this is easy. But the cost of neglect is systemic failure. Every line of code and every parameter in the weights needs to be accounted for.
