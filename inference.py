import numpy as np
import librosa
import model
import torch
from pathlib import Path, PurePath

device = torch.device("cuda:0")
MODELS = ["fcn", "musicnn","crnn","sample","se","attention", "hcnn"]

TAGS = np.array(['genre---downtempo', 'genre---ambient', 'genre---rock', 'instrument---synthesizer', 'genre---atmospheric', 'genre---indie', 'instrument---electricpiano', 'genre---newage', 'instrument---strings', 'instrument---drums', 'instrument---drummachine', 'genre---techno', 'instrument---guitar', 'genre---alternative', 'genre---easylistening', 'genre---instrumentalpop', 'genre---chillout', 'genre---metal', 'mood/theme---happy', 'genre---lounge', 'genre---reggae', 'genre---popfolk', 'genre---orchestral', 'instrument---acousticguitar', 'genre---poprock', 'instrument---piano', 'genre---trance', 'genre---dance', 'instrument---electricguitar', 'genre---soundtrack', 'genre---house', 'genre---hiphop', 'genre---classical', 'mood/theme---energetic', 'genre---electronic', 'genre---world', 'genre---experimental', 'instrument---violin', 'genre---folk', 'mood/theme---emotional', 
    'instrument---voice', 'instrument---keyboard', 'genre---pop', 
    'instrument---bass', 'instrument---computer', 'mood/theme---film', 
    'genre---triphop', 'genre---jazz', 'genre---funk', 'mood/theme---relaxing'])
models = {
            "fcn": model.FCN().to(device),
            "musicnn": model.Musicnn(dataset="jamendo").to(device),
            "crnn": model.CRNN().to(device),
            "sample": model.SampleCNN().to(device),
            "se": model.SampleCNNSE().to(device),
            "attention": model.CNNSA().to(device),
            "hcnn": model.HarmonicCNN().to(device),
        }

input_lengths = {
            "fcn": 29 * 16000,
            "musicnn": 3 * 16000,
            "crnn": 29 * 16000,
            "sample": 59049,
            "se": 59049,
            "attention": 15 * 16000,
            "hcnn": 5 * 16000,
        }

SAMPLE_RATE = 16000

def infer(path,model_path,key="fcn"):

    model = models[key]
    S = torch.load(model_path)
    if 'spec.mel_scale.fb' in S.keys():
      model.spec.mel_scale.fb = S['spec.mel_scale.fb']
    model.load_state_dict(S)
    model.eval()

    input_length = input_lengths[key]

    signal, _ = librosa.core.load(path, sr=SAMPLE_RATE)
    length = len(signal)
    x = torch.stack(
            [torch.Tensor(signal[i:i+input_length]) for i in range(0,input_length*int(length/input_length), input_length)],
            dim=0
            )
    out, representation = model(x.to(device))
    
    return torch.mean(representation, dim=0, keepdim=True).detach().cpu()

def embedding_gen(parent_dir, model_path, key):
    parent_dir = Path(parent_dir)
    dir_path = parent_dir.joinpath("genres_original")
    embeddings_dir = parent_dir.joinpath("embeddings").joinpath(key)
    embeddings_dir.mkdir(parents=True, exist_ok=True)
    for genre in dir_path.iterdir():
        genre_name = PurePath(genre).parts[-1]
        torch.save(
                    torch.stack([infer(path=file_path, model_path=model_path, key=key).detach().cpu() for file_path in genre.iterdir()]),
                    embeddings_dir.joinpath(genre_name)
                    )
        print(genre_name+" done")
        
def run(parent_dir, models=MODELS,model_parent_path = '/content/musical-shrooms/models/jamendo/'):
    parent_dir = Path(parent_dir)
    model_parent_path = Path(parent_dir)

    for model in models:
      ix_dict = dict()
      model_path = model_parent_path.joinpath(model).joinpath('best_model.pth')
      dir_path = parent_dir.joinpath("genres_original")
      embeddings_dir = parent_dir.joinpath("embeddings").joinpath(model)
      embeddings_dir.mkdir(parents=True, exist_ok=True)
      print(model + " running!")
      for genre in dir_path.iterdir():
          li = []
          genre_name = genre.parts[-1]
          if not '_' in genre_name:
              ix_dict[genre_name] = list()
              for file_path in genre.iterdir():
                try:
                  ix_dict[genre_name].append(file_path.parts[-1])
                  li.append(infer(path=file_path, model_path=model_path, key=model).detach().cpu())
                except:
                  print(file_path)
                  break
              torch.save(
                          torch.stack(li),
                          embeddings_dir.joinpath(genre_name)
                          )
              print(genre_name+" done")
              with open(embeddings_dir.joinpath('original_ix_dict.pickle'), 'wb') as handle:
                pickle.dump(ix_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
    for model in models:
      ix_dict = dict()
      model_path = model_parent_path.joinpath(model).joinpath('best_model.pth')
      dir_path = parent_dir.joinpath("genres_ood")
      embeddings_dir = parent_dir.joinpath("embeddings").joinpath(model)
      embeddings_dir.mkdir(parents=True, exist_ok=True)
      print(model + " running!")
      for genre in dir_path.iterdir():
          li = []
          genre_name = genre.parts[-1]
          ix_dict[genre_name] = list()
          for file_path in genre.iterdir():
            try:
              ix_dict[genre_name].append(file_path.parts[-1])
              li.append(infer(path=file_path, model_path=model_path, key=model).detach().cpu())
            except:
              print(file_path)
              break
          torch.save(
                      torch.stack(li),
                      embeddings_dir.joinpath(genre_name)
                      )
          print(genre_name+" done")
          with open(embeddings_dir.joinpath('ood_ix_dict.pickle'), 'wb') as handle:
            pickle.dump(ix_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)