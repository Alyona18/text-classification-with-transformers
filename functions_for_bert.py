# -*- coding: utf-8 -*-
"""functions_for_BERT.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1xrKlf4a3r_RWZ84zaS3yQ0HqtbV_qXNY
"""

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AdamW, get_linear_schedule_with_warmup

from dataset_bert import CustomDataset

class Classifier:
  
   
   def __init__(self, model, tokenizer, out_features, epochs, n_classes = 2):
      self.model = model
      self.tokenizer = tokenizer
      self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
      self.max_len = 512
      self.epochs = epochs
      self.out_features = out_features
      self.model.classifier = torch.nn.Linear(self.out_features, n_classes)
      self.model.to(self.device)


   def preparation(self, X_train, y_train, X_valid, y_valid):
      self.train_set = CustomDataset(X_train, y_train, self.tokenizer)
      self.valid_set = CustomDataset(X_valid, y_valid, self.tokenizer)

      self.train_loader = DataLoader(self.train_set, batch_size=2, shuffle=True)
      self.valid_loader = DataLoader(self.valid_set, batch_size=2, shuffle=True)

      self.optimizer = AdamW(self.model.parameters(), lr=2e-5, correct_bias=False)
      self.scheduler = get_linear_schedule_with_warmup(
         self.optimizer,
         num_warmup_steps=0,
         num_training_steps=len(self.train_loader) * self.epochs
         )
      self.loss_fn = torch.nn.CrossEntropyLoss().to(self.device)


   def fit(self):
      self.model = self.model.train()
      losses = []
      correct_predictions = 0

      for data in self.train_loader:
         input_ids = data["input_ids"].to(self.device)
         attention_mask = data["attention_mask"].to(self.device)
         targets = data["targets"].to(self.device)

         outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask
            )

         preds = torch.argmax(outputs.logits, dim=1)
         loss = self.loss_fn(outputs.logits, targets)

         correct_predictions += torch.sum(preds == targets)

         losses.append(loss.item())
            
         loss.backward()
         torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
         self.optimizer.step()
         self.scheduler.step()
         self.optimizer.zero_grad()

      train_acc = correct_predictions.double() / len(self.train_set)
      train_loss = np.mean(losses)
      return train_acc, train_loss


   def eval(self):
      self.model = self.model.eval()
      losses = []
      correct_predictions = 0

      with torch.no_grad():
         for data in self.valid_loader:
            input_ids = data["input_ids"].to(self.device)
            attention_mask = data["attention_mask"].to(self.device)
            targets = data["targets"].to(self.device)

            outputs = self.model(
               input_ids=input_ids,
               attention_mask=attention_mask
            )
 
            preds = torch.argmax(outputs.logits, dim=1)
            loss = self.loss_fn(outputs.logits, targets)
            correct_predictions += torch.sum(preds == targets)
            losses.append(loss.item())
        
      val_acc = correct_predictions.double() / len(self.valid_set)
      val_loss = np.mean(losses)
      return val_acc, val_loss


   def train(self,name):
      all_valid_loss = []
      all_train_loss = []
      all_valid_acc = []
      all_train_acc = []

      model_save_path = '/content/drive/MyDrive/??????/models/'+name
      best_accuracy = 0
      for epoch in range(self.epochs):
         print(f'Epoch {epoch + 1}/{self.epochs}')
         train_acc, train_loss = self.fit()
         print(f'Train loss {train_loss} accuracy {train_acc}')
         all_train_loss.append(train_loss)
         all_train_acc.append(train_acc)
    
         val_acc, val_loss = self.eval()
         print(f'Val loss {val_loss} accuracy {val_acc}')
         print('-' * 10)
         all_valid_loss.append(val_loss)
         all_valid_acc.append(val_acc)
      if val_acc > best_accuracy:
                torch.save(self.model, model_save_path)
                best_accuracy = val_acc
                
      return all_valid_loss, all_valid_acc, all_train_loss, all_train_acc           


   def predict(self, text):
      encoding = self.tokenizer.encode_plus(
         text,
         add_special_tokens=True,
         max_length=self.max_len,
         return_token_type_ids=False,
         truncation=True,
         padding='max_length',
         return_attention_mask=True,
         return_tensors='pt',
         )
    
      out = {
         'text': text,
         'input_ids': encoding['input_ids'].flatten(),
         'attention_mask': encoding['attention_mask'].flatten()
         }
    
      input_ids = out["input_ids"].to(self.device)
      attention_mask = out["attention_mask"].to(self.device)
    
      outputs = self.model(
         input_ids=input_ids.unsqueeze(0),
         attention_mask=attention_mask.unsqueeze(0)
         )
    
      prediction = torch.argmax(outputs.logits, dim=1).cpu().numpy()[0]

      return prediction
