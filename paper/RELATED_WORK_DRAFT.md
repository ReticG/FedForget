# Related Work Section Draft - FedForget

## 2. Related Work

### 2.1 Federated Learning

**Federated Averaging (FedAvg)** [McMahan et al., 2017] introduced the foundational framework for distributed learning where clients perform local training on private data and a central server aggregates model updates. The standard FedAvg aggregation is:

$$\theta_g^{t+1} = \sum_{i=1}^N \frac{n_i}{n_{\text{total}}} \theta_i^{t+1}$$

where $\theta_g$ is the global model, $\theta_i$ is client $i$'s model, and $n_i$ is the number of samples.

**Non-IID Data Challenges.** Real-world federated learning faces significant challenges from non-identically distributed (Non-IID) data across clients [Li et al., 2020]. Common approaches to address this include:
- FedProx [Li et al., 2020]: Adds proximal term to local objectives
- FedNova [Wang et al., 2020]: Normalizes local updates
- SCAFFOLD [Karimireddy et al., 2020]: Uses control variates

However, none of these methods address the unlearning problem under Non-IID settings, which is the focus of our work.

**Privacy in Federated Learning.** While federated learning provides privacy-by-design, recent attacks show vulnerabilities:
- Gradient inversion attacks [Zhu et al., 2019] can reconstruct training data
- Model inversion attacks [Fredrikson et al., 2015] extract sensitive features
- Membership inference attacks [Shokri et al., 2017] determine if a sample was in training data

These privacy concerns motivate the need for effective unlearning mechanisms in federated settings.

### 2.2 Machine Unlearning

**Exact Unlearning.** The ideal unlearning approach is to retrain the model from scratch without the forgotten data [Cao & Yang, 2015]. However, this is computationally prohibitive, especially in federated learning where retraining requires re-coordinating all clients over multiple rounds.

**Approximate Unlearning Methods:**

1. **SISA Training** [Bourtoule et al., 2021]: Partitions data into shards and aggregates multiple models. Unlearning requires retraining only affected shards. While efficient, it requires upfront knowledge of future unlearning requests and increases model complexity.

2. **Gradient-Based Unlearning** [Guo et al., 2020]: Uses influence functions to approximate the effect of removing data. Limited to convex models and small datasets.

3. **Data Augmentation** [Golatkar et al., 2020]: Trains on synthetic "noisy" versions of forgotten data to reduce influence. Requires careful noise calibration and may degrade model utility.

4. **Knowledge Distillation for Unlearning** [Chundawat et al., 2023]: Uses teacher-student framework where the student learns to forget specific data while retaining other knowledge. Our work extends this idea to federated settings with dual teachers.

**Federated Unlearning (Recent).** Emerging work addresses unlearning in federated learning:

- **FedEraser** [Liu et al., 2021]: Calibrates each client update to enable rapid unlearning. Requires storing historical updates and still needs multiple rounds.

- **Submodel-Based Unlearning** [Halimi et al., 2022]: Trains client-specific submodels that can be easily removed. High storage overhead and potential utility loss.

- **Incremental Learning Approaches** [Wu et al., 2023]: Uses continual learning techniques but doesn't provide strong forgetting guarantees.

**Gap in Literature:** Existing federated unlearning methods either (1) require excessive communication rounds, (2) need significant storage overhead, or (3) lack strong privacy guarantees. FedForget addresses these limitations through dual-teacher distillation and dynamic weight adjustment.

### 2.3 Knowledge Distillation

**Original Knowledge Distillation** [Hinton et al., 2015]: Student model learns from teacher's soft predictions:

$$\mathcal{L}_{\text{KD}} = \text{KL}(p_s(x; \theta_s) \| p_t(x; \theta_t))$$

where $p_s$ and $p_t$ are student and teacher predictions, typically with temperature scaling.

**Distillation Variants:**

1. **Self-Distillation** [Zhang et al., 2019]: Model learns from its own predictions across different architectures or training stages.

2. **Multi-Teacher Distillation** [You et al., 2017]: Student learns from multiple teachers. Typically averages teacher predictions, but our approach uses teachers for different purposes (retention vs forgetting).

3. **Contrastive Distillation** [Tian et al., 2020]: Uses contrastive learning objectives for knowledge transfer.

**Negative Distillation.** While traditional distillation transfers knowledge positively, recent work explores "negative" distillation:
- Adversarial distillation for robustness [Papernot et al., 2016]
- Unlearning through reversed gradients [Tarun et al., 2023]

**Our Innovation:** FedForget introduces **dual-teacher distillation** where:
- Teacher A (global model): Positive distillation for knowledge retention
- Teacher B (local model) or gradient ascent: Negative learning for data forgetting
- Balance controlled by hyperparameter α

This dual mechanism is novel in federated unlearning and enables effective forgetting while preserving utility.

### 2.4 Privacy Evaluation via Membership Inference Attacks

**Membership Inference Attacks (MIA)** [Shokri et al., 2017] test if a specific sample was in the training data:

1. **Threshold-Based MIA** [Yeom et al., 2018]: Uses model confidence as threshold. Simple but effective baseline.

2. **Shadow Model Attack** [Shokri et al., 2017]: Trains shadow models to mimic target model behavior, then trains an attack classifier. More powerful but expensive.

3. **Metric-Based MIA** [Song & Mittal, 2021]: Uses modified loss or prediction entropy.

**MIA for Unlearning Evaluation:** MIA is a natural metric for unlearning effectiveness:
- **High ASR (Attack Success Rate)** on forgotten data → Poor unlearning (data still influences model)
- **Low ASR (~50%, random guessing)** → Good unlearning (data influence removed)

We use both SimpleMIA (threshold-based) and Shadow Model Attack to comprehensively evaluate FedForget's privacy guarantee.

### 2.5 Positioning of FedForget

FedForget uniquely combines:
1. **Federated learning** framework for distributed unlearning
2. **Dual-teacher distillation** for balanced retention and forgetting
3. **Dynamic weight adjustment** for accelerated forgetting propagation
4. **Strong privacy guarantee** validated via MIA

Unlike prior work, FedForget:
- Works effectively under **diverse Non-IID settings** (α=0.1 to 1.0)
- Achieves **2.3× speedup** over retraining with minimal utility loss
- Provides **best privacy protection** (ASR=48.36%, closest to 50%)
- Requires **minimal system modifications** (only weight parameter and standard distillation)

---

## Key References (Draft)

**Federated Learning:**
- McMahan et al. "Communication-Efficient Learning of Deep Networks from Decentralized Data." AISTATS 2017.
- Li et al. "Federated Optimization in Heterogeneous Networks." MLSys 2020.

**Machine Unlearning:**
- Bourtoule et al. "Machine Unlearning." IEEE S&P 2021.
- Guo et al. "Certified Data Removal from Machine Learning Models." ICML 2020.
- Liu et al. "The Right to be Forgotten in Federated Learning." INFOCOM 2022.

**Knowledge Distillation:**
- Hinton et al. "Distilling the Knowledge in a Neural Network." NeurIPS 2015.
- You et al. "Learning from Multiple Teacher Networks." KDD 2017.

**Privacy Attacks:**
- Shokri et al. "Membership Inference Attacks Against Machine Learning Models." IEEE S&P 2017.
- Yeom et al. "Privacy Risk in Machine Learning: Analyzing the Connection to Overfitting." CSF 2018.

---

*This draft positions FedForget within the broader research landscape, clearly identifies the research gap, and highlights our unique contributions.*
