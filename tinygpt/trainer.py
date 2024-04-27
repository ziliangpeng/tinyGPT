"""
Simple training loop; Boilerplate that could apply to any arbitrary neural network,
so nothing in this file really has anything to do with GPT specifically.
"""

import time
from collections import defaultdict

# import torch
import tinygrad
from tinygpt import tinyloader
from tinygpt import tinyutils
from tinygpt.utils import CfgNode as CN

class Trainer:

    @staticmethod
    def get_default_config():
        C = CN()
        # device to train on
        C.device = 'auto'
        # dataloder parameters
        C.num_workers = 4
        # optimizer parameters
        C.max_iters = None
        C.batch_size = 64
        C.learning_rate = 3e-4
        C.betas = (0.9, 0.95)
        C.weight_decay = 0.1 # only applied on matmul weights
        C.grad_norm_clip = 1.0
        return C

    def __init__(self, config, model, train_dataset):
        self.config = config
        self.model = model
        self.optimizer = None
        self.train_dataset = train_dataset
        self.callbacks = defaultdict(list)

        # determine the device we'll train on
        if config.device == 'auto':
            # self.device = 'cuda' if torc.cuda.is_available() else 'cpu'
            # we will deal with cuda later
            config.device = 'cpu'
        else:
            self.device = config.device
        # self.model = self.model.to(self.device)
        # print("running on device", self.device)

        # variables that will be assigned to trainer class later for logging and etc
        self.iter_num = 0
        self.iter_time = 0.0
        self.iter_dt = 0.0

    def add_callback(self, onevent: str, callback):
        self.callbacks[onevent].append(callback)

    def set_callback(self, onevent: str, callback):
        self.callbacks[onevent] = [callback]

    def trigger_callbacks(self, onevent: str):
        for callback in self.callbacks.get(onevent, []):
            callback(self)

    def run(self):
        model, config = self.model, self.config

        # setup the optimizer
        self.optimizer = model.configure_optimizers(config)

        # setup the dataloader
        train_loader = tinyloader.DataLoader(
            self.train_dataset,
            sampler=tinyloader.RandomSampler(self.train_dataset, replacement=True, num_samples=int(1e10)),
            shuffle=False,
            pin_memory=True,
            batch_size=config.batch_size,
            num_workers=config.num_workers,
        )

        # model.train()
        with tinygrad.tensor.Tensor.train():
            self.iter_num = 0
            self.iter_time = time.time()
            data_iter = iter(train_loader)
            while True:

                # fetch the next batch (x, y) and re-init iterator if needed
                try:
                    batch = next(data_iter)
                except StopIteration:
                    data_iter = iter(train_loader)
                    batch = next(data_iter)
                # batch = [t.to(self.device) for t in batch]
                # print(batch)
                # print(type(batch))
                # print(batch.shape)
                x, y = batch
                # print(x)
                # print(type(x))
                # print(x.shape)
                x = tinygrad.tensor.Tensor(x.numpy())
                y = tinygrad.tensor.Tensor(y.numpy())

                btime = time.time()
                # forward the model
                logits, self.loss = model(x, y)
                print(f'debug 1, time: {time.time() - btime}')
                btime = time.time()
                # print(logits.numpy())

                # backprop and update the parameters
                # model.zero_grad(set_to_none=True)
                self.optimizer.zero_grad()
                self.loss.backward()
                print(f'debug 2, time: {time.time() - btime}')
                btime = time.time()
                # params = tinygrad.nn.state.get_parameters(model)
                # tinyutils.clip_grad_norm_(params, config.grad_norm_clip)
                self.optimizer.step()
                print(f'debug 3, time: {time.time() - btime}')
                btime = time.time()

                self.trigger_callbacks('on_batch_end')
                self.iter_num += 1
                tnow = time.time()
                self.iter_dt = tnow - self.iter_time
                self.iter_time = tnow

                # termination conditions
                # if config.max_iters is not None and self.iter_num >= config.max_iters:
                if self.iter_num >= 10:
                    break
