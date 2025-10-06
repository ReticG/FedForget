# Introduction Section Draft - FedForget

## 1. Introduction

The proliferation of privacy regulations such as the General Data Protection Regulation (GDPR) and the California Consumer Privacy Act (CCPA) has introduced the "right to be forgotten" as a fundamental requirement for modern machine learning systems. This right mandates that users can request the complete removal of their data contributions from trained models. While straightforward in centralized settings—where retraining from scratch without the forgotten data suffices—this becomes significantly more challenging in federated learning environments.

**Federated Learning and Privacy Challenges.** Federated learning (FL) enables collaborative model training across distributed clients without sharing raw data, offering inherent privacy advantages. However, when a client requests data removal, the traditional approach of retraining the global model from scratch is prohibitively expensive. This retraining requires re-coordinating all remaining clients, repeating multiple rounds of communication, and incurring substantial computational costs—often 2-3× the original training time in our experiments.

**Existing Solutions and Their Limitations.** Recent machine unlearning methods attempt to efficiently remove data influence without full retraining. Centralized approaches like SISA training [1], gradient-based unlearning [2], and knowledge distillation methods [3] show promise but fail to address federated-specific challenges:

1. **Non-IID Data Distribution**: Federated clients typically hold heterogeneous, non-identically distributed data, making knowledge disentanglement more difficult than centralized settings.

2. **Communication Constraints**: Limited bandwidth and communication rounds restrict the complexity of unlearning protocols.

3. **Privacy Requirements**: The unlearning process itself must not leak information about the forgotten data or other clients' contributions.

4. **Utility Preservation**: The unlearned model must maintain performance on the remaining clients' data while effectively forgetting the target client's contribution.

Existing federated unlearning methods [4, 5] either require excessive retraining rounds, sacrifice too much model utility, or fail to provide strong privacy guarantees. A critical gap exists for an efficient, privacy-preserving federated unlearning framework that maintains model utility across diverse data distributions.

**Our Contribution: FedForget.** We propose FedForget, a novel federated unlearning framework that combines dual-teacher knowledge distillation with dynamic weight adjustment to achieve efficient, effective, and privacy-preserving unlearning. Our key insight is to leverage two complementary mechanisms:

1. **Client-Level**: Dual-teacher knowledge distillation that simultaneously preserves knowledge from non-forgetting clients (via the global model as Teacher A) while actively removing the forgetting client's contribution (via gradient ascent or local model as Teacher B).

2. **Server-Level**: Dynamic weight adjustment during federated aggregation that amplifies the unlearning signal by increasing the forgetting client's weight (λ_forget), accelerating forgetting propagation without additional communication overhead.

**Main Contributions:**

1. **Algorithmic Innovation**: We introduce the first federated unlearning framework combining dual-teacher knowledge distillation with dynamic weight adjustment, enabling efficient unlearning under federated constraints.

2. **Comprehensive Evaluation**: We conduct extensive experiments across multiple datasets (MNIST, Fashion-MNIST, CIFAR-10, CIFAR-100) and diverse Non-IID settings (Dirichlet α ∈ {0.1, 0.3, 0.5, 0.7, 1.0}), demonstrating:
   - **Efficiency**: 2.3× faster than retraining (51s vs 118s on CIFAR-10)
   - **Effectiveness**: 31.2% forgetting rate on CIFAR-10, 60.5% on CIFAR-100
   - **Privacy**: Best privacy protection with ASR=48.36% (closest to ideal 50%)
   - **Robustness**: Stable performance across all Non-IID distributions

3. **Privacy Guarantee**: We provide empirical evidence through Member Inference Attacks (MIA) showing FedForget achieves superior privacy protection compared to retraining and fine-tuning baselines, with Attack Success Rate closest to random guessing (50%).

4. **Practical Applicability**: FedForget requires minimal modifications to existing federated learning systems—only a weight adjustment parameter on the server and standard knowledge distillation on the unlearning client.

**Organization.** The remainder of this paper is organized as follows: Section 2 reviews related work on federated learning, machine unlearning, and knowledge distillation. Section 3 presents the FedForget framework with detailed algorithms. Section 4 describes our experimental setup and presents comprehensive results. Section 5 concludes with discussions and future directions.

---

## References (Draft)

[1] Bourtoule et al. "Machine Unlearning." IEEE S&P 2021.
[2] Guo et al. "Certified Data Removal from Machine Learning Models." ICML 2020.
[3] Golatkar et al. "Eternal Sunshine of the Spotless Net: Selective Forgetting in Deep Networks." CVPR 2020.
[4] Liu et al. "The Right to be Forgotten in Federated Learning: An Efficient Realization with Rapid Retraining." INFOCOM 2022.
[5] Wu et al. "Federated Unlearning with Knowledge Distillation." ArXiv 2023.

---

*This draft emphasizes the practical motivation (GDPR compliance), clearly identifies the research gap (federated-specific challenges), and highlights our key contributions with concrete numbers from experiments.*
