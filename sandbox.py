import pickle

path = "/Users/nikunjlad/data/CUB/birds/"

with open(path + 'bird_captions.pickle', 'rb') as f:
    bc = pickle.load(f)

print(bc[3])