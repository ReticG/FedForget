"""
成员推断攻击 (Membership Inference Attack)

用于评估机器遗忘的隐私保护效果。
原理: 如果遗忘成功，攻击者应该无法区分数据是否在训练集中。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from sklearn.metrics import roc_auc_score, accuracy_score
from typing import Dict, List, Tuple


class ShadowModelAttack:
    """
    基于影子模型的MIA攻击

    步骤:
    1. 训练影子模型 (模仿目标模型的训练过程)
    2. 收集影子模型在成员/非成员数据上的预测
    3. 训练攻击模型 (分类器) 区分成员/非成员
    4. 在目标模型上测试攻击成功率
    """

    def __init__(self, device='cuda'):
        self.device = device
        self.attack_model = None

    def extract_features(self, model: nn.Module, data_loader, device) -> np.ndarray:
        """
        从模型预测中提取特征用于MIA

        特征包括:
        - Top-k预测概率
        - 预测熵
        - 正确类别的概率
        """
        model.eval()
        features = []

        with torch.no_grad():
            for inputs, labels in data_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                probs = F.softmax(outputs, dim=1)

                # 提取特征
                batch_features = []
                for i in range(len(labels)):
                    prob = probs[i].cpu().numpy()
                    label = labels[i].item()

                    # Top-3 概率
                    top3_probs = np.sort(prob)[-3:]

                    # 预测熵
                    entropy = -np.sum(prob * np.log(prob + 1e-10))

                    # 正确类别概率
                    correct_prob = prob[label]

                    # 最大概率
                    max_prob = np.max(prob)

                    feature = np.concatenate([
                        top3_probs,
                        [entropy, correct_prob, max_prob]
                    ])
                    batch_features.append(feature)

                features.extend(batch_features)

        return np.array(features)

    def train_attack_model(self,
                          member_features: np.ndarray,
                          non_member_features: np.ndarray):
        """
        训练攻击模型 (简单的逻辑回归分类器)

        Args:
            member_features: 成员数据的特征
            non_member_features: 非成员数据的特征
        """
        from sklearn.linear_model import LogisticRegression

        # 准备训练数据
        X = np.vstack([member_features, non_member_features])
        y = np.hstack([
            np.ones(len(member_features)),  # 成员=1
            np.zeros(len(non_member_features))  # 非成员=0
        ])

        # 训练攻击模型
        self.attack_model = LogisticRegression(max_iter=1000, random_state=42)
        self.attack_model.fit(X, y)

        # 计算训练准确率
        train_acc = self.attack_model.score(X, y)
        return train_acc

    def evaluate_attack(self,
                       target_member_features: np.ndarray,
                       target_non_member_features: np.ndarray) -> Dict[str, float]:
        """
        评估攻击成功率

        返回:
            - accuracy: 攻击准确率 (越低越好，说明遗忘效果好)
            - auc: ROC AUC分数
            - tpr: True Positive Rate (成员识别率)
            - tnr: True Negative Rate (非成员识别率)
        """
        if self.attack_model is None:
            raise ValueError("攻击模型未训练，请先调用train_attack_model")

        # 准备测试数据
        X_test = np.vstack([target_member_features, target_non_member_features])
        y_test = np.hstack([
            np.ones(len(target_member_features)),
            np.zeros(len(target_non_member_features))
        ])

        # 预测
        y_pred = self.attack_model.predict(X_test)
        y_pred_proba = self.attack_model.predict_proba(X_test)[:, 1]

        # 计算指标
        accuracy = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_pred_proba)

        # TPR和TNR
        member_preds = y_pred[:len(target_member_features)]
        non_member_preds = y_pred[len(target_member_features):]

        tpr = np.mean(member_preds == 1)  # 成员被正确识别的比例
        tnr = np.mean(non_member_preds == 0)  # 非成员被正确识别的比例

        return {
            'accuracy': accuracy * 100,
            'auc': auc,
            'tpr': tpr * 100,
            'tnr': tnr * 100
        }


class SimpleMIA:
    """
    简化的MIA攻击 - 基于损失/置信度阈值

    原理: 成员数据通常有更低的损失和更高的置信度
    """

    @staticmethod
    def evaluate_threshold_attack(model: nn.Module,
                                  member_loader,
                                  non_member_loader,
                                  device='cuda') -> Dict[str, float]:
        """
        基于阈值的MIA攻击

        使用损失值作为判断依据:
        - 低损失 → 判定为成员
        - 高损失 → 判定为非成员
        """
        model.eval()
        criterion = nn.CrossEntropyLoss(reduction='none')

        # 收集成员数据的损失
        member_losses = []
        with torch.no_grad():
            for inputs, labels in member_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                losses = criterion(outputs, labels)
                member_losses.extend(losses.cpu().numpy())

        # 收集非成员数据的损失
        non_member_losses = []
        with torch.no_grad():
            for inputs, labels in non_member_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                losses = criterion(outputs, labels)
                non_member_losses.extend(losses.cpu().numpy())

        member_losses = np.array(member_losses)
        non_member_losses = np.array(non_member_losses)

        # 使用损失中位数作为阈值
        threshold = np.median(np.concatenate([member_losses, non_member_losses]))

        # 攻击: loss < threshold → 成员
        member_correct = np.sum(member_losses < threshold)
        non_member_correct = np.sum(non_member_losses >= threshold)

        total = len(member_losses) + len(non_member_losses)
        accuracy = (member_correct + non_member_correct) / total * 100

        tpr = member_correct / len(member_losses) * 100
        tnr = non_member_correct / len(non_member_losses) * 100

        # 计算AUC
        y_true = np.concatenate([
            np.ones(len(member_losses)),
            np.zeros(len(non_member_losses))
        ])
        y_scores = -np.concatenate([member_losses, non_member_losses])  # 负损失作为分数
        auc = roc_auc_score(y_true, y_scores)

        return {
            'accuracy': accuracy,
            'auc': auc,
            'tpr': tpr,
            'tnr': tnr,
            'member_loss_mean': np.mean(member_losses),
            'non_member_loss_mean': np.mean(non_member_losses),
            'threshold': threshold
        }


def evaluate_unlearning_privacy(
    model: nn.Module,
    forget_loader,  # 被遗忘的数据 (应该像非成员)
    retain_loader,  # 保留的训练数据 (成员)
    test_loader,    # 测试数据 (非成员)
    device='cuda'
) -> Dict[str, float]:
    """
    评估遗忘后的隐私保护效果

    理想情况:
    - forget_loader应该被误判为非成员 (低TPR)
    - retain_loader应该仍是成员 (高TPR)
    - 总体攻击成功率应该接近50% (随机猜测水平)
    """

    # 使用简单阈值攻击
    results = {}

    # 1. Forget vs Test (理想: 无法区分)
    mia = SimpleMIA()
    forget_vs_test = mia.evaluate_threshold_attack(
        model, forget_loader, test_loader, device
    )

    results['forget_vs_test'] = {
        'accuracy': forget_vs_test['accuracy'],
        'auc': forget_vs_test['auc'],
        'forget_loss': forget_vs_test['member_loss_mean'],
        'test_loss': forget_vs_test['non_member_loss_mean']
    }

    # 2. Retain vs Test (保留数据仍应可区分)
    retain_vs_test = mia.evaluate_threshold_attack(
        model, retain_loader, test_loader, device
    )

    results['retain_vs_test'] = {
        'accuracy': retain_vs_test['accuracy'],
        'auc': retain_vs_test['auc'],
        'retain_loss': retain_vs_test['member_loss_mean'],
        'test_loss': retain_vs_test['non_member_loss_mean']
    }

    # 3. Forget vs Retain (理想: Forget像非成员)
    forget_vs_retain = mia.evaluate_threshold_attack(
        model, forget_loader, retain_loader, device
    )

    results['forget_vs_retain'] = {
        'accuracy': forget_vs_retain['accuracy'],
        'auc': forget_vs_retain['auc'],
        'forget_loss': forget_vs_retain['member_loss_mean'],
        'retain_loss': forget_vs_retain['non_member_loss_mean']
    }

    return results
