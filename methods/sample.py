class SupervisedContrastiveLoss(nn.Module):

    '''
    Usage:
    self.supconloss  = SupervisedContrastiveLoss()
    con_loss = self.supconloss( F.normalize(out, dim=1), y_a_i)
    '''
    def __init__(self, temperature=0.5):
        super(SupervisedContrastiveLoss, self).__init__()
        self.temperature = temperature

    def forward(self, features, labels):
        batch_size = features.size(0)
        mask = torch.eye(batch_size).to(features.device)

        # Compute similarity
        sim = torch.mm(features, features.t().contiguous()) / self.temperature
        sim = sim - mask * 1e9
        sim = sim.softmax(dim=1)

        # Compute ground truth
        labels = labels.unsqueeze(1)
        target_mask = (labels == labels.t()).float().to(features.device)
        target_mask = target_mask - mask * 1e9
        target = target_mask.softmax(dim=1)

        # Compute contrastive loss
        eps = 1e-7
        loss = -(target * (sim + eps).log()).sum(dim=1).mean()
        # loss = -(target * sim.log()).sum(dim=1).mean()
        return loss

import torch
import torch.nn.functional as F
'''
Not working
'''
def supervised_contrastive_loss(features, n_support):
    batch_size = features.size(0)
    n_samples = features.size(1)

    # Compute the pairwise cosine distances between anchor and negative samples
    anchor_features = features[:, :n_support, :]
    negative_features = features[:, n_support:, :]
    cosine_distances = torch.matmul(anchor_features, negative_features.transpose(1, 2))

    # Compute the numerator and denominator for the contrastive loss
    numerator = torch.exp(cosine_distances)
    denominator = torch.sum(numerator, dim=-1, keepdim=True) + 1e-8  # Add epsilon to avoid division by zero

    # Compute the supervised contrastive loss
    loss_sup_con = -torch.log(numerator / denominator).mean()

    return loss_sup_con

class FSLSupConLoss(nn.Module):
    def __init__(self, temperature=0.5):
        super(FSLSupConLoss, self).__init__()
        self.temperature = temperature

    def forward(self, features, labels):
        device = (torch.device('cuda') if features.is_cuda else torch.device('cpu'))

        # Ensure features tensor is [batch_size, n_views, feature_dim]
        if len(features.shape) < 3:
            features = features.unsqueeze(1)

        batch_size = features.shape[0]
        labels = labels.contiguous().view(-1, 1)
        if labels.shape[0] != batch_size:
            raise ValueError('Num of labels does not match num of features')

        # Create a mask for positive pairs
        mask = torch.eq(labels, labels.T).float().to(device)

        contrast_count = features.shape[1]
        contrast_feature = torch.cat(torch.unbind(features, dim=1), dim=0)

        anchor_feature = contrast_feature
        anchor_count = contrast_count

        # Compute logits
        anchor_dot_contrast = torch.div(
            torch.matmul(anchor_feature, contrast_feature.T),
            self.temperature)
        # For numerical stability
        logits_max, _ = torch.max(anchor_dot_contrast, dim=1, keepdim=True)
        logits = anchor_dot_contrast - logits_max.detach()

        # Tile mask
        mask = mask.repeat(anchor_count, contrast_count)
        # Mask-out self-contrast cases
        logits_mask = torch.scatter(
            torch.ones_like(mask),
            1,
            torch.arange(batch_size * anchor_count).view(-1, 1).to(device),
            0
        )
        mask = mask * logits_mask

        # Compute log_prob
        exp_logits = torch.exp(logits) * logits_mask
        log_prob = logits - torch.log(exp_logits.sum(1, keepdim=True))

        # Compute mean of log-likelihood over positive
        mean_log_prob_pos = (mask * log_prob).sum(1) / mask.sum(1)

        # Loss
        loss = - mean_log_prob_pos
        loss = loss.view(anchor_count, batch_size).mean()

        return loss

class CTMLoss(nn.Module):
    def __init__(self):
        super(CTMLoss, self).__init__()

    def forward(self, features, labels):
        # Compute pairwise distance
        dist = torch.cdist(features, features, p=2)

        # Compute ground truth
        labels = labels.unsqueeze(1)
        target_mask = (labels == labels.t()).float().to(features.device)

        # Compute CTM loss
        loss = (target_mask * dist).sum() / target_mask.sum()
        return loss
import torch
import torch.nn.functional as F

def cross_task_metric_loss(model, support_set, query_set):
    # support_set and query_set are tensors containing support and query samples, respectively
    # model is the adapted model with the updated parameters (e.g., f_theta_e_prime)

    # Compute logits for the query samples
    logits = model(query_set[:, 0])  # Assuming query_set[:, 0] contains the query samples

    # Compute the feature prototypes for each class in the support set
    class_prototypes = []
    for c in range(len(support_set)):
        class_samples = support_set[c][:, 0]  # Assuming support_set[c][:, 0] contains the support samples for class c
        class_features = model(class_samples)
        class_prototype = torch.mean(class_features, dim=0)
        class_prototypes.append(class_prototype)
    class_prototypes = torch.stack(class_prototypes)

    # Compute the cross-task metric loss
    loss_ctm = F.cross_entropy(logits, query_set[:, 1], reduction='mean')  # Assuming query_set[:, 1] contains the query labels

    # Compute the probability p(y_q^a_i = c | x_q^a_i) for each query sample
    feature_queries = model(query_set[:, 0])
    distances = torch.cdist(feature_queries, class_prototypes, p=2)  # Compute the Euclidean distances
    exp_distances = torch.exp(-distances)
    class_probabilities = exp_distances / torch.sum(exp_distances, dim=1, keepdim=True)

    # Update the cross-task metric loss based on probabilities
    loss_ctm *= torch.sum(class_probabilities[torch.arange(len(query_set)), query_set[:, 1]])

    return loss_ctm
class HyperParameterGenerator(nn.Module):
    def __init__(self):
        super(HyperParameterGenerator, self).__init__()
        self.fc1 = nn.Linear(4, 10)  # Assuming the input dimension is 4
        self.fc2 = nn.Linear(10, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = torch.sigmoid(self.fc2(x))
        return x
import torch
import torch.nn as nn

class HyperParameterGenerator(nn.Module):
    def __init__(self, input_dim, hidden_dim):
        super(HyperParameterGenerator, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = torch.sigmoid(self.fc3(x))
        return x

# Usage example:
# input_dim = dimension of layer-wise means of gradients and weights (e.g., 2 * feat_dim)
# hidden_dim = dimension of the hidden layer in the MLP
# hyperparameter_generator = HyperParameterGenerator(input_dim, hidden_dim)
# beta = hyperparameter_generator(tau) * beta_initial

class MAML(MetaTemplate):
    def __init__(self, model_func, n_way, n_support, approx=False):
        super(MAML, self).__init__(model_func, n_way, n_support, change_way=False)

        self.loss_fn = nn.CrossEntropyLoss()
        self.supervised_contrastive_loss = SupervisedContrastiveLoss()
        self.ctm_loss = CTMLoss()
        self.hyperparameter_generator = HyperParameterGenerator()

        self.classifier = backbone.Linear_fw(self.feat_dim, n_way)
        self.classifier.bias.data.fill_(0)

        self.n_task = 4  # meta-batch, meta update every meta batch
        self.task_update_num = 5
        self.train_lr = 0.01  # this is the inner loop learning rate
        self.approx = approx  # first order approx.
        self.beta = torch.ones(1).cuda()  # initial proportion beta

    def set_forward(self, x, is_feature=False):
        assert is_feature == False, 'MAML do not support fixed feature'

        x = x.cuda()
        x_var = Variable(x)
        x_a_i = x_var[:, :self.n_support, :, :, :].contiguous().view(self.n_way * self.n_support, *x.size()[2:])  # support data 
        y_a_i = Variable(torch.from_numpy(np.repeat(range(self.n_way), self.n_support))).cuda()  # label for support data

        fast_parameters = list(self.parameters())  # the first gradient calculated in line 45 is based on original weight
        for weight in self.parameters():
            weight.fast = None
        self.zero_grad()

        for task_step in range(self.task_update_num):
            scores = self.forward(x_a_i)

            # Compute the CE loss
            loss_ce = self.loss_fn(scores, y_a_i)

            # Compute the supervised contrastive loss
            support_features = self.feature.forward(x_a_i)
            loss_sup_con = self.supervised_contrastive_loss(support_features, y_a_i)

            # Compute the layer-wise means of gradients and weights
            gradients = torch.autograd.grad(outputs=loss_sup_con, inputs=self.parameters(), create_graph=True)
            mean_gradients = torch.mean(torch.stack([torch.mean(g) for g in gradients]))
            mean_weights = torch.mean(torch.stack([torch.mean(p) for p in self.parameters()]))
            tau = torch.cat([mean_gradients.unsqueeze(0), mean_weights.unsqueeze(0)], dim=0)

            # Generate the task-adaptive hyperparameter
            self.beta = self.hyperparameter_generator(tau) * self.beta

            # Compute adapted weights
            loss = loss_ce + self.beta * loss_sup_con
            grad = torch.autograd.grad(loss, fast_parameters, create_graph=True)
            if self.approx:
                grad = [g.detach() for g in grad]  # do not calculate gradient of gradient if using first order approximation
            fast_parameters = []
            for k, weight in enumerate(self.parameters()):
                if weight.fast is None:
                    weight.fast = weight - self.train_lr * grad[k]  # create weight.fast 
                else:
                    weight.fast = weight.fast - self.train_lr * grad[k]  # create an updated weight.fast
                fast_parameters.append(weight.fast)  # gradients calculated in line 45 are based on newest fast weight

        # feed forward query data
        x_b_i = x_var[:, self.n_support:, :, :, :].contiguous().view(self.n_way * self.n_query, *x.size()[2:])  # query data
        scores = self.forward(x_b_i)
        return scores

    def set_forward_loss(self, x):
        scores = self.set_forward(x, is_feature=False)
        y_b_i = Variable(torch.from_numpy(np.repeat(range(self.n_way), self.n_query))).cuda()
        loss = self.loss_fn(scores, y_b_i)

        return loss

    def train_loop(self, epoch, train_loader, optimizer):  # overwrite parrent function
        print_freq = 10
        avg_loss = 0
        task_count = 0
        loss_all = []

        optimizer.zero_grad()

        # train
        for i, (x, _) in enumerate(train_loader):
            self.n_query = x.size(1) - self.n_support
            assert self.n_way == x.size(0), "MAML do not support way change"

            loss = self.set_forward_loss(x)
            avg_loss = avg_loss + loss.item()
            loss_all.append(loss)

            task_count += 1

            if task_count == self.n_task:  # MAML update several tasks at one time
                loss_q = torch.stack(loss_all).sum(0)
                loss_value = loss_q.item()
                loss_q.backward()
                optimizer.step()

                task_count = 0
                loss_all = []
            optimizer.zero_grad()
            if i % print_freq == 0:
                print('Epoch {:d} | Batch {:d}/{:d} | Loss {:f}'.format(epoch, i, len(train_loader), avg_loss / float(i + 1)))

def train_loop(self, epoch, train_loader, optimizer): 
    print_freq = 10
    avg_loss = 0
    task_count = 0
    loss_all = []

    optimizer.zero_grad()

    # train
    for i, (x, _) in enumerate(train_loader):
        self.n_query = x.size(1) - self.n_support
        assert self.n_way == x.size(0), "MAML does not support way change"

        loss = self.set_forward_loss(x)
        avg_loss = avg_loss + loss.item()
        loss_all.append(loss)

        task_count += 1

        if task_count == self.n_task:  # MAML update several tasks at one time
            loss_q = torch.stack(loss_all).sum(0)
            
            # Add the CTM loss to the outer optimization loop
            x_a_i = x[:, :self.n_support, :, :, :].contiguous().view(self.n_way * self.n_support, *x.size()[2:])  # support data 
            support_features = self.feature.forward(x_a_i)
            loss_ctm = self.ctm_loss(support_features, y_a_i)  # CTM loss is computed only based on the support features
            loss_q += (1 - self.gamma) * loss_ctm
            
            loss_value = loss_q.item()
            loss_q.backward()
            optimizer.step()

            task_count = 0
            loss_all = []
        optimizer.zero_grad()
        if i % print_freq == 0:
            print('Epoch {:d} | Batch {:d}/{:d} | Loss {:f}'.format(epoch, i, len(train_loader), avg_loss / float(i + 1)))    

def test_loop(self, test_loader, return_std=False):  # overwrite parrent function
        correct = 0
        count = 0
        acc_all = []
        loss_all = []

        iter_num = len(test_loader)
        for i, (x, _) in enumerate(tqdm(test_loader, desc='Testing', leave=False)):
            self.n_query = x.size(1) - self.n_support
            assert self.n_way == x.size(0), "MAML do not support way change"
            correct_this, count_this = self.correct(x)

            x_a_i = x[:, :self.n_support, :, :, :].contiguous().view(self.n_way * self.n_support, *x.size()[2:])  # support data 
            support_features = self.feature.forward(x_a_i)
            x_b_i = x[:, self.n_support:, :, :, :].contiguous().view(self.n_way * self.n_query, *x.size()[2:])  # query data
            query_features = self.feature.forward(x_b_i)
            loss_ctm = self.ctm_loss(torch.cat([support_features, query_features], dim=0),
                                     torch.cat([y_a_i, y_b_i], dim=0))
            loss_all.append(loss_ctm)

            acc_all.append(correct_this / count_this * 100)

        loss_mean = torch.mean(torch.stack(loss_all)).item()
        loss_q = loss_mean + (1 - self.gamma) * loss_mean
        loss_q.backward()
        optimizer.step()

        acc_all = np.asarray(acc_all)
        acc_mean = np.mean(acc_all)
        acc_std = np.std(acc_all)
        print('%d Test’)


def test_loop(self, test_loader, return_std=False): 
    correct = 0
    count = 0
    acc_all = []

    iter_num = len(test_loader)
    for i, (x, _) in enumerate(tqdm(test_loader, desc='Testing', leave=False)):
        self.n_query = x.size(1) - self.n_support
        assert self.n_way == x.size(0), "MAML does not support way change"
        correct_this, count_this = self.correct(x)

        acc_all.append(correct_this / count_this * 100)

    acc_all = np.asarray(acc_all)
    acc_mean = np.mean(acc_all)
    acc_std = np.std(acc_all)
    print('%d Test Acc = %4.2f%% ± %4.2f%%' %(iter_num, acc_mean, 1.96 * acc_std / np.sqrt(iter_num)))
    if return_std:
        return acc_mean, acc_std
    else:
        return acc_mean
def outer_loop_optimization_loss(model, gamma, main_task_query_set, auxiliary_tasks):
    # model is the adapted model with the updated parameters (e.g., f_theta_prime)
    # gamma is the balance hyperparameter for the main and auxiliary tasks
    # main_task_query_set is the query set for the main task Tmi
    # auxiliary_tasks is a list of query sets for the auxiliary tasks, each represented as (support_set, query_set)

    # Compute the cross-entropy loss for the main task
    logits_main_task = model(main_task_query_set[:, 0])
    loss_ce_main_task = F.cross_entropy(logits_main_task, main_task_query_set[:, 1], reduction='mean')  # Assuming main_task_query_set[:, 1] contains the main task query labels

    # Compute the cross-task metric loss for each auxiliary task and sum them up
    loss_ctm_auxiliary_tasks = 0
    for support_set, query_set in auxiliary_tasks:
        loss_ctm_auxiliary_tasks += cross_task_metric_loss(model, support_set, query_set)

    # Compute the outer-loop optimization loss
    loss_outer = gamma * loss_ce_main_task + (1 - gamma) * loss_ctm_auxiliary_tasks

    return loss_outer