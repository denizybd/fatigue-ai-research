'''
Author: Zhou Shuwei             
2024.05.15
A stable version of PINN with customizable variables and relationships
'''

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler
from functools import partial

def pearson_r(y_true, y_pred):
    ''' PCC for testing '''
    y_true = y_true.detach().numpy()
    y_pred = y_pred.detach().numpy()
    
    numerator = np.sum((y_pred - np.mean(y_pred)) * (y_true - np.mean(y_true)))
    denominator = (np.sum((y_pred - np.mean(y_pred))**2) * np.sum((y_true - np.mean(y_true))**2))**0.5
    
    r = numerator / denominator
    return r

def r2_score(y_true, y_pred):
    '''R2 score calculation '''
    y_true = y_true.detach().numpy()
    y_pred = y_pred.detach().numpy()
    sst = np.sum((y_true - np.mean(y_true)) ** 2)     # Sum of Squares total
    sse = np.sum((y_true - y_pred) ** 2)  # Sum of Squares error
    r2 = 1 - sse / sst    
    return r2

class PINN(nn.Module):
    def __init__(self, input_size, hidden_layer_sizes, stress_index=0, other_constraints=None, input_transform=None, activation_function=nn.SELU(), dropout_rate=0.1, l2_lambda=0.01):
        super(PINN, self).__init__()
        self.l2_lambda = l2_lambda
        self.activation_function = activation_function
        self.stress_index = stress_index  # stress index
        self.other_constraints = other_constraints  # others physical constraints
        self.input_transform = input_transform  

        # set hidden layer sizes
        layer_sizes = [input_size] + hidden_layer_sizes + [1]
        self.layers = nn.ModuleList()
        for i in range(len(layer_sizes) - 1):
            self.layers.append(nn.Linear(layer_sizes[i], layer_sizes[i+1]))

        self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x_in, return_derivatives=False):
        if not x_in.requires_grad:
            x_in = x_in.detach().requires_grad_(True)

        # define input transformation
        if self.input_transform is not None:
            x = self.input_transform(x_in)
        else:
            x = x_in

        # forward pass
        for i, layer in enumerate(self.layers[:-1]):  # exclude the last layer
            x = layer(x)
            x = self.activation_function(x)
            if self.training:
                x = self.dropout(x)

        # last layer without activation function
        lg_N = self.layers[-1](x)

        if not return_derivatives:
            return lg_N

        lg_N_summed = lg_N.sum()

        # first order gradient
        lg_N_grad = torch.autograd.grad(lg_N_summed, x_in, create_graph=True)[0]

        # second order gradient 
        lg_N_grad_summed = lg_N_grad.sum()
        lg_N_grad2 = torch.autograd.grad(lg_N_grad_summed, x_in, create_graph=True, allow_unused=True)[0]

        # substract the stress gradient
        lg_N_S_grad = lg_N_grad[:, self.stress_index].unsqueeze(1)
        lg_N_SS_grad = lg_N_grad2[:, self.stress_index].unsqueeze(1) if lg_N_grad2 is not None else None

        # other physical constraints gradients (or second order gradients)
        other_grads = {}
        other_grad2s = {}
        for idx in range(x_in.shape[1]):
            if idx == self.stress_index:
                continue
            other_grads[idx] = lg_N_grad[:, idx].unsqueeze(1)
            other_grad2s[idx] = lg_N_grad2[:, idx].unsqueeze(1) if lg_N_grad2 is not None else None

        return lg_N, lg_N_S_grad, lg_N_SS_grad, other_grads, other_grad2s
    
    def tanh(self, x, beta):
        return torch.tanh(beta * x ** 2)

    def G(self, x, beta):
        return torch.relu(x*self.tanh(x, beta))
    
    def relu(self, x, beta):
        return torch.relu(x)

    def combined_loss(self, lg_N_pred, lg_N_S_grad, lg_N_SS_grad, other_grads, other_grad2s, y_true, weight, beta, return_individual_losses=False, physical_loss_type='relu'):
        # data loss
        data_loss = nn.MSELoss()(lg_N_pred, y_true)

        if physical_loss_type == 'relu':
            # stress physical loss
            phys_loss_S = torch.mean(self.relu(lg_N_S_grad, beta))  # First-order derivative of stress should be less than 0
            phys_loss_SS = torch.mean(self.relu(-lg_N_SS_grad, beta)) if lg_N_SS_grad is not None else 0  # Second-order derivative of stress should be greater than 0
            stress_phys_loss = phys_loss_S + phys_loss_SS

        elif physical_loss_type == 'G':
            # stress physical loss
            phys_loss_S = torch.mean(self.G(lg_N_S_grad, beta))
            phys_loss_SS = torch.mean(self.G(-lg_N_SS_grad, beta)) if lg_N_SS_grad is not None else 0
            stress_phys_loss = phys_loss_S + phys_loss_SS

        # Initialize other physical losses
        other_phys_loss = 0
        individual_other_phys_losses = {}

        # Calculate physical losses for other variables
        if self.other_constraints:
            for idx, constraint in self.other_constraints.items():
                grad = other_grads[idx]
                grad2 = other_grad2s[idx]
                expected_sign = constraint['value']  # 1 represents positive, -1 represents negative

                if constraint['type'] == 'grad_sign':
                    if physical_loss_type == 'relu':
                        constraint_loss = torch.mean(self.relu(-expected_sign * grad, beta))
                    elif physical_loss_type == 'G':
                        constraint_loss = torch.mean(self.G(-expected_sign * grad, beta))

                    # Update total other physical loss
                    other_phys_loss += constraint_loss
                    # Save individual physical loss
                    individual_other_phys_losses[idx] = constraint_loss.item()

        # Total physical loss
        phys_loss = stress_phys_loss + other_phys_loss

        # Total loss
        combined_loss = (1 - weight) * data_loss + weight * phys_loss

        # L2 regularization
        l2_reg = 0
        for param in self.parameters():
            l2_reg += torch.norm(param)
        combined_loss += self.l2_lambda * l2_reg

        if return_individual_losses:
            return combined_loss, data_loss, phys_loss_S, phys_loss_SS, other_phys_loss, individual_other_phys_losses
        else:
            return combined_loss
        
    # def optimize(self, x, y, epochs, lr_adam, lr_lbfgs, weight, beta, switch_epoch, physical_loss_type='relu'):
    #     optimizer_adam = optim.Adam(self.parameters(), lr=lr_adam)
    #     optimizer_lbfgs = optim.LBFGS(self.parameters(), lr=lr_lbfgs, max_iter=20)

    #     # Initialize history records
    #     self.loss_curve = []
    #     self.data_loss_history = []
    #     self.phys_loss_S_history = []
    #     self.phys_loss_SS_history = []
    #     self.other_phys_loss_history = []
    #     self.R2_curve = []
        
    #     # Initialize individual loss history for each physical constraint
    #     self.individual_other_phys_losses_history = {idx: [] for idx in self.other_constraints.keys()}

    #     for epoch in range(epochs):
    #         optimizer = optimizer_adam if epoch < switch_epoch else optimizer_lbfgs

    #         def closure():
    #             optimizer.zero_grad()
    #             x_input = x
    #             if not x_input.requires_grad:
    #                 x_input = x_input.detach().requires_grad_(True)
    #             lg_N_pred, lg_N_S_grad, lg_N_SS_grad, other_grads, other_grad2s = self.forward(x_input, return_derivatives=True)
    #             loss, data_loss, phys_loss_S, phys_loss_SS, other_phys_loss, individual_other_phys_losses = self.combined_loss(
    #                 lg_N_pred, lg_N_S_grad, lg_N_SS_grad, other_grads, other_grad2s, y, weight, beta, return_individual_losses=True, physical_loss_type=physical_loss_type)
    #             loss.backward(retain_graph=True)
    #             self.current_loss = loss.item()
    #             self.current_data_loss = data_loss.item()
    #             self.current_phys_loss_S = phys_loss_S.item()
    #             self.current_phys_loss_SS = phys_loss_SS.item()
    #             self.current_other_phys_loss = other_phys_loss.item()
    #             self.current_R2 = r2_score(y.detach(), lg_N_pred.detach())

    #             # Update individual_other_phys_losses_history
    #             for idx, loss_value in individual_other_phys_losses.items():
    #                 # Check if loss_value is a tensor
    #                 if isinstance(loss_value, torch.Tensor):
    #                     self.individual_other_phys_losses_history[idx].append(loss_value.item())
    #                 else:
    #                     self.individual_other_phys_losses_history[idx].append(float(loss_value))

    #             return loss

    #         if optimizer is optimizer_lbfgs:
    #             optimizer.step(closure)
    #         else:
    #             closure()
    #             optimizer.step()

    #         # Update history records
    #         self.loss_curve.append(self.current_loss)
    #         self.data_loss_history.append(self.current_data_loss)
    #         self.phys_loss_S_history.append(self.current_phys_loss_S)
    #         self.phys_loss_SS_history.append(self.current_phys_loss_SS)
    #         self.other_phys_loss_history.append(self.current_other_phys_loss)
    #         self.R2_curve.append(self.current_R2)

    #     return  self.loss_curve, self.R2_curve, self.data_loss_history, self.phys_loss_S_history, self.phys_loss_SS_history, self.other_phys_loss_history, self.individual_other_phys_losses_history

    # def predict(self, x):
    #     self.eval()
    #     with torch.no_grad():
    #         lg_N_pred = self.forward(x, return_derivatives=False)
    #     return lg_N_pred

    def optimize(self, x, y, epochs, lr_adam, lr_lbfgs, weight, beta, switch_epoch, physical_loss_type='relu', return_final_derivatives=False):
        optimizer_adam = optim.Adam(self.parameters(), lr=lr_adam)
        optimizer_lbfgs = optim.LBFGS(self.parameters(), lr=lr_lbfgs, max_iter=20)

        # Initialize history records
        self.loss_curve = []
        self.data_loss_history = []
        self.phys_loss_S_history = []
        self.phys_loss_SS_history = []
        self.other_phys_loss_history = []
        self.R2_curve = []
        
        # Initialize individual loss history for each physical constraint
        self.individual_other_phys_losses_history = {idx: [] for idx in self.other_constraints.keys()}

        for epoch in range(epochs):
            optimizer = optimizer_adam if epoch < switch_epoch else optimizer_lbfgs

            def closure():
                optimizer.zero_grad()
                x_input = x
                if not x_input.requires_grad:
                    x_input = x_input.detach().requires_grad_(True)
                lg_N_pred, lg_N_S_grad, lg_N_SS_grad, other_grads, other_grad2s = self.forward(x_input, return_derivatives=True)
                loss, data_loss, phys_loss_S, phys_loss_SS, other_phys_loss, individual_other_phys_losses = self.combined_loss(
                    lg_N_pred, lg_N_S_grad, lg_N_SS_grad, other_grads, other_grad2s, y, weight, beta, return_individual_losses=True, physical_loss_type=physical_loss_type)
                loss.backward(retain_graph=True)
                self.current_loss = loss.item()
                self.current_data_loss = data_loss.item()
                self.current_phys_loss_S = phys_loss_S.item()
                self.current_phys_loss_SS = phys_loss_SS.item() if isinstance(phys_loss_SS, torch.Tensor) else phys_loss_SS
                self.current_other_phys_loss = other_phys_loss.item()
                self.current_R2 = r2_score(y.detach(), lg_N_pred.detach())

                # Update individual_other_phys_losses_history
                for idx, loss_value in individual_other_phys_losses.items():
                    if isinstance(loss_value, torch.Tensor):
                        self.individual_other_phys_losses_history[idx].append(loss_value.item())
                    else:
                        self.individual_other_phys_losses_history[idx].append(float(loss_value))

                return loss

            if optimizer is optimizer_lbfgs:
                optimizer.step(closure)
            else:
                closure()
                optimizer.step()

            # Update history records
            self.loss_curve.append(self.current_loss)
            self.data_loss_history.append(self.current_data_loss)
            self.phys_loss_S_history.append(self.current_phys_loss_S)
            self.phys_loss_SS_history.append(self.current_phys_loss_SS)
            self.other_phys_loss_history.append(self.current_other_phys_loss)
            self.R2_curve.append(self.current_R2)

        if return_final_derivatives:
            # After training, calculate and record partial derivatives for each data point
            x_input = x.detach().requires_grad_(True)
            self.eval()  # Set model to evaluation mode

            # Calculate predictions
            lg_N_pred = self.forward(x_input, return_derivatives=False)

            # Calculate first-order derivatives
            lg_N_pred_sum = lg_N_pred.sum()
            lg_N_grad = torch.autograd.grad(lg_N_pred_sum, x_input, create_graph=True)[0]

            # Calculate second-order derivatives
            lg_N_grad_sum = lg_N_grad.sum()
            lg_N_grad2 = torch.autograd.grad(lg_N_grad_sum, x_input, create_graph=False)[0]

            # Extract first and second-order partial derivatives of stress
            lg_N_S_grad = lg_N_grad[:, self.stress_index].unsqueeze(1)
            lg_N_SS_grad = lg_N_grad2[:, self.stress_index].unsqueeze(1)

            # Extract first-order partial derivatives of other variables
            other_grads = {}
            for idx in range(x_input.shape[1]):
                if idx == self.stress_index:
                    continue
                other_grads[idx] = lg_N_grad[:, idx].unsqueeze(1)

            # Convert results to NumPy arrays
            lg_N_S_grad = lg_N_S_grad.detach().cpu().numpy()
            lg_N_SS_grad = lg_N_SS_grad.detach().cpu().numpy()
            other_grads_numpy = {idx: grad.detach().cpu().numpy() for idx, grad in other_grads.items()}

            # Include partial derivatives in return value
            return (self.loss_curve, self.R2_curve, self.data_loss_history, self.phys_loss_S_history,
                    self.phys_loss_SS_history, self.other_phys_loss_history, self.individual_other_phys_losses_history,
                    lg_N_S_grad, lg_N_SS_grad, other_grads_numpy)
        else:
            # When partial derivatives are not needed, only return history records
            return (self.loss_curve, self.R2_curve, self.data_loss_history, self.phys_loss_S_history,
                    self.phys_loss_SS_history, self.other_phys_loss_history, self.individual_other_phys_losses_history)


    def predict(self, x, return_derivatives=False, return_second_derivatives=False):
        self.eval()
        x_input = x.detach().requires_grad_(True)
        lg_N_pred = self.forward(x_input, return_derivatives=False)  # Shape: (n_samples, 1)

        if return_derivatives or return_second_derivatives:
            # Calculate first-order derivatives
            grad_outputs = torch.ones_like(lg_N_pred)  # Shape: (n_samples, 1)
            lg_N_grad = torch.autograd.grad(
                outputs=lg_N_pred,
                inputs=x_input,
                grad_outputs=grad_outputs,
                create_graph=return_second_derivatives,
                retain_graph=True,
                only_inputs=True
            )[0]  # Shape: (n_samples, n_features)

            # Extract first-order partial derivative of stress
            lg_N_S_grad = lg_N_grad[:, self.stress_index].unsqueeze(1)  # Shape: (n_samples, 1)

            if return_second_derivatives:
                # Calculate second-order derivatives
                lg_N_S_grad_flat = lg_N_S_grad.view(-1)  # Shape: (n_samples,)
                second_grad_list = []
                for idx in range(lg_N_S_grad_flat.shape[0]):
                    grad2 = torch.autograd.grad(
                        outputs=lg_N_S_grad_flat[idx],
                        inputs=x_input,
                        create_graph=False,
                        retain_graph=True
                    )[0][idx, self.stress_index]
                    second_grad_list.append(grad2)

                lg_N_SS_grad = torch.stack(second_grad_list).unsqueeze(1)  # Shape: (n_samples, 1)
                lg_N_SS_grad = lg_N_SS_grad.detach().cpu().numpy()
            else:
                lg_N_SS_grad = None

            # Extract first-order partial derivatives of other variables
            other_grads = {}
            for idx in range(x_input.shape[1]):
                if idx == self.stress_index:
                    continue
                other_grads[idx] = lg_N_grad[:, idx].unsqueeze(1)

            lg_N_S_grad = lg_N_S_grad.detach().cpu().numpy()
            other_grads_numpy = {idx: grad.detach().cpu().numpy() for idx, grad in other_grads.items()}
            lg_N_pred_numpy = lg_N_pred.detach().cpu().numpy()

            return lg_N_pred_numpy, lg_N_S_grad, lg_N_SS_grad, other_grads_numpy
        else:
            return lg_N_pred
        
        
    def evaluate(self, x, y):
        lg_N_pred = self.predict(x)
        return r2_score(y, lg_N_pred)

    def save_model(self, path):
        torch.save(self.state_dict(), path)

if __name__ == "__main__":

    # generate data for testing
    data_size = 44
    hidden_layer_sizes = [10, 10]  # Two hidden layers with 10 neurons each

    # Example input variables: stress, temperature, humidity
    stress = torch.randn((data_size, 1))
    temperature = torch.randn((data_size, 1))
    humidity = torch.randn((data_size, 1))
    y = torch.randn((data_size, 1))  # Fatigue life

    # Combine input variables into a tensor
    x = torch.cat((stress, temperature, humidity), dim=1)

    # Convert to NumPy arrays for standardization
    input_data = x.detach().numpy()
    target_data = y.detach().numpy()

    scaler = StandardScaler()
    input_data_scaled = scaler.fit_transform(input_data)
    x_scaled = torch.tensor(input_data_scaled, dtype=torch.float32)
    x_scaled.requires_grad = True  # Ensure it's a leaf variable with gradients enabled
    y_scaled = torch.tensor(target_data, dtype=torch.float32)

    # Pre-calculate mean and standard deviation of temperature and humidity
    temperature_mean = x_scaled[:, 1].mean()
    temperature_std = x_scaled[:, 1].std()
    humidity_mean = x_scaled[:, 2].mean()
    humidity_std = x_scaled[:, 2].std()

    # Custom input transformation function
    def input_transform(x_in):
        # No transformation for stress
        stress_transformed = x_in[:, 0].unsqueeze(1)
        # Standardize temperature
        temperature_transformed = (x_in[:, 1] - temperature_mean) / temperature_std
        temperature_transformed = temperature_transformed.unsqueeze(1)
        # Square transformation for humidity
        humidity_transformed = (x_in[:, 2] ** 2).unsqueeze(1)
        # Combine transformed variables
        return torch.cat((stress_transformed, temperature_transformed, humidity_transformed), dim=1)

    # Define physical constraints for other variables
    other_constraints = {
        1: {'type': 'grad_sign', 'value': -1},  # First-order derivative of temperature should be negative
        2: {'type': 'grad_sign', 'value': -1}  # First-order derivative of humidity should be negative
    }

    # Create model, passing input_transform and other constraints
    model = PINN(
        input_size=3,
        hidden_layer_sizes=hidden_layer_sizes,
        stress_index=0,
        other_constraints=other_constraints,
        input_transform=input_transform
    )

    epochs = 1000
    lr_adam = 0.001
    lr_lbfgs = 0.01
    weight = 0.5
    beta = 100
    switch_epoch = 500

    # Train model
    model.optimize(x_scaled, y_scaled, epochs, lr_adam, lr_lbfgs, weight, beta, switch_epoch)

    # Prepare test data
    test_data = x_scaled[0].unsqueeze(0)

    # Make prediction
    prediction = model.predict(test_data)
    print(f"Prediction: {prediction[0].item()}")
