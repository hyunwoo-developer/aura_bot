# BottlePy web programming micro-framework
import bottle
from bottle import request, route, template, get, post, delete
import os
import os.path
import traceback
import json
import socket

hostname = socket.gethostname()
IP = socket.gethostbyname(hostname)

# import apps from subfolders
for dir in os.listdir():
    appFilename = os.path.join(dir, dir + '.py')
    if  os.path.isfile(appFilename):
        print("Importing " + dir + "...")
        try:
            __import__(dir + '.' + dir)
        except:
            print("Failed to import " + dir + ":")
            msg = traceback.format_exc()
            print(msg)
            bottle.route('/' + dir, 'GET', 
                lambda msg=msg, dir=dir: 
                    reportImportError(dir, msg))

def reportImportError(dir, msg):
    return """<html><body>
        <h1>There was an error importing application {0}</h1>
        <pre>{1}</pre>
        </body></html>""".format(dir, msg)

@route('/<filename:path>')
def send_static(filename):
    """Helper handler to serve up static game assets.

    (Borrowed from BottlePy documentation examples.)"""
    if str(filename).find('.py') == -1:
        return bottle.static_file(filename, root='.')
    else:
        return """You do not have sufficient permissions to access this page."""

@route('/', method='Get')
def index():
    if os.path.isfile("index.html"):
        return bottle.static_file("index.html", root='.')
    else:
        return """<html><body>Nothing to see here... move along now.
        Or, create an index.html file.</body></html>"""

from keras.models import Sequential, Model
from keras.layers.embeddings import Embedding
from keras.layers import Input, Activation, Dense, Permute, Dropout
from keras.layers import add, dot, concatenate
from keras.layers import LSTM
from keras.utils.data_utils import get_file
from keras.preprocessing.sequence import pad_sequences
from functools import reduce
import tarfile
import numpy as np
import re
import codecs

from scipy.spatial import distance
import json


# In[2]:
def tokenize(sent):
    return [x.strip() for x in re.split(r'(\W+)?', sent) if x.strip()]

def parse_stories(lines, only_supporting=False):
    data = []
    story = []
    for line in lines:
        line = line.strip()
        nid, line = line.split(' ', 1)
        nid = int(nid)
        if nid == 1:
            story = []
        if '\t' in line:
            q, a, supporting = line.split('\t')
            q = tokenize(q)
            substory = None
            if only_supporting:
                # Only select the related substory
                supporting = map(int, supporting.split())
                substory = [story[i - 1] for i in supporting]
            else:
                # Provide all the substories
                substory = [x for x in story if x]
            data.append((substory, q, a))
            story.append('')
        else:
            sent = tokenize(line)
            story.append(sent)
    return data

def get_stories(f, only_supporting=False, max_length=None):
    data = parse_stories(f.readlines(), only_supporting=only_supporting)
    flatten = lambda data: reduce(lambda x, y: x + y, data)
    data = [(flatten(story), q, answer) for story, q, answer in data
            if not max_length or len(flatten(story)) < max_length]
    return data

def vectorize_stories(data):
    inputs, queries, answers = [], [], []
    for story, query, answer in data:
        inputs.append([word_idx[w] for w in story])
        queries.append([word_idx[w] for w in query])
        answers.append(word_idx[answer])
    return (pad_sequences(inputs, maxlen=story_maxlen),
            pad_sequences(queries, maxlen=query_maxlen),
            np.array(answers))


# In[3]:
data = 'aurabot'
direc = './'
train_stories = get_stories(codecs.open(direc + data + '.txt', 'r', 'utf-8'))

vocab = set()
for story, q, answer in train_stories:
    vocab |= set(story + q + [answer])
vocab = sorted(vocab)

vocab_size = len(vocab) + 1
story_maxlen = max(map(len, (x for x, _, _ in train_stories)))
query_maxlen = max(map(len, (x for _, x, _ in train_stories)))

print('-')
print('????????? ?????? :', vocab_size, '???????????? ??????')
print('????????? ?????? :', story_maxlen, '??????')
print('?????? :', query_maxlen, '??????')
print('?????? ????????? ??????:', len(train_stories))
print('-')
print('????????? ?????? ???????????? ????????? (?????????, ??????, ??????):')
print(train_stories[0])
print('-')

word_idx = dict((c, i + 1) for i, c in enumerate(vocab))
inputs_train, queries_train, answers_train = vectorize_stories(train_stories)
print('????????? : ????????????', inputs_train.shape)
print('?????? : ????????????', queries_train.shape)
print('?????? : (1 ?????? 0)??? ????????? ?????? ??????', answers_train.shape)
print('-')


# In[4]:
# ??????
input_sequence = Input((story_maxlen,))
question = Input((query_maxlen,))

input_encoder_m = Sequential()
input_encoder_m.add(Embedding(input_dim=vocab_size, output_dim=64))
input_encoder_m.add(Dropout(0.3))

input_encoder_c = Sequential()
input_encoder_c.add(Embedding(input_dim=vocab_size, output_dim=query_maxlen))
input_encoder_c.add(Dropout(0.3))

question_encoder = Sequential()
question_encoder.add(Embedding(input_dim=vocab_size, output_dim=64, input_length=query_maxlen))
question_encoder.add(Dropout(0.3))

input_encoded_m = input_encoder_m(input_sequence)
input_encoded_c = input_encoder_c(input_sequence)
question_encoded = question_encoder(question)

match = dot([input_encoded_m, question_encoded], axes=(2, 2))
match = Activation('softmax')(match)

response = add([match, input_encoded_c])
response = Permute((2, 1))(response)

answer = concatenate([response, question_encoded])
answer = LSTM(32)(answer)
answer = Dropout(0.3)(answer)
answer = Dense(vocab_size)(answer)
answer = Activation('softmax')(answer)

model = Model([input_sequence, question], answer)
model.compile(optimizer='rmsprop', loss='sparse_categorical_crossentropy', metrics=['accuracy'])


# In[5]:
model.fit([inputs_train, queries_train], answers_train, batch_size=1, epochs=150)


@route('/chat', method=['GET','POST'])
def getUserMsg():
    msg = request.json.get('message')
    botResult = botAnswer.sendQ(msg)
    if (botResult == '') or (botResult == None):
        return {'msg' : "??? ???????????? ????????????."}
    else:
        return {'msg' : botResult}

#----- ?????? ?????? ?????? -----
def vocab_result(x, vocab):
    if x.argmax() != 0: return vocab[int(x.argmax())-1]
    else: return False
    
def v_s(data, s_m):
    a = []
    for i in data:
        if i == None:
            a.append(word_idx['UNK'])
        else:
            a.append(word_idx[i])
    return (pad_sequences([a], maxlen=s_m))

def ref_result(result1, result2, mode='detail'):
    a = distance.euclidean(result1[0], result2[0])
    c =  vocab_result(result2[0], vocab)
    d = max(result2[0])
    if c != False:
        b = c
    if mode == 'detail':
        print('detail_ref / acc :', a, '/', max(result2[0]))
    
    if mode == 'simple' or mode == 'detail':
        print('????????? :', a)
        print('????????? :', d)
        if b:
            print('?????? :', ''.join(b))
        else:
            print('????????????')
    return a, d

def answer_result(result1, threshold=0.9):
    a, b = [], []
    x = vocab_result(result1[0], vocab)
    if x != False:
        if max(result1[0]) > threshold:
            a.append(x)
            a.append(" ")
            a.append(max(result1[0]))
            a.append(" ")
            b.append(x)
            b.append(" ")
        else:
            return False, False
    
    if a != []:
        return ''.join([str(i) for i in a]), ''.join([str(i) for i in b])
    else:
        return False, False


# In[7]:


# ?????? ????????????
with codecs.open('./answers.json', 'r', encoding='UTF-8') as json_data:
    answers_data = json.load(json_data)['answers']
json_data.close()
an = 1  # ????????? ?????? ???????????? ?????????
print('Sample : ['+answers_data[an-1]['ID']+']', answers_data[an-1]['AN'])

# In[8]:
#?????? ??? ???????????? ?????? ??? ????????? ??????
class InputAura:
    def __init__(self):
        self.Input_Data = []

    def sendQ(self, Q):
        try:
            threshold = 0.9      #0.9
            ref_threshold = 1.5      #1.5
            
            q_data = tokenize(Q)
            ref_data,Input_Data_A = [], []
            m_acc = []
            results = []
            result_no = 0
            final_answer = None
            
            #?????? flatten
            Input_Data_F = [y for x in self.Input_Data for y in x]
            
            #?????? ??????
            print('???????????? : ??????')
            results.append(model.predict([v_s(tokenize('UNK'), story_maxlen), v_s(q_data, query_maxlen)]))
            _, a = ref_result(results[0], results[0], mode='simple')     #detail / simple / none
            m_acc.append(a)
            
            result_no += 1
            print()

            #??? ?????? ??? ?????? ?????????
            j = []
            for i in self.Input_Data:
                j.extend(i)
                print('???????????? :', end="")
                for f in j:
                    print(vocab[f-1], end=" ")
                print()
                
                result = model.predict([pad_sequences([j], story_maxlen, truncating='post'), v_s(q_data, query_maxlen)])
                a, b = ref_result(results[0], result, mode='simple')     #detail / simple / none
                
                if a < ref_threshold:
                    results.append(result)
                    m_acc.append(b)
                    result_no += 1
                print()
            
            #?????? ????????????
            rank_1 = np.argmax(m_acc)

            for i in range(rank_1):
                ref_data.append(self.Input_Data[i])

            #????????? ??????
            print('??????????????? :', end=' ')
            an_no, f_an_no = answer_result(results[0], threshold=threshold)
            if an_no == False:
                an_no, f_an_no = '?????? ????????? ???????????????', '?????? ????????? ???????????????'
            print(an_no)

            #???????????? ??????
            print('?????????????????? :', end=' ')
            an_A, f_an_A = answer_result(results[rank_1], threshold=threshold)
            
            if an_A == False:
                an_A, f_an_A = '?????? ????????? ???????????????', '?????? ????????? ???????????????'
            print(an_A)

            if ref_data == []:
                final_answer = f_an_no
            else:
                final_answer = f_an_A

            #?????? ?????? ????????????
            x_d = []
            for i in v_s(q_data, query_maxlen):
                for j in reversed(i):
                    if j != 0:
                        x_d.insert(0, j)

            self.Input_Data = ref_data + [x_d]

            #??????
            print("=================================")
            print('?????? :',q_data)
            print('???????????? :', end=" ")
            for i in Input_Data_F:
                print(vocab[i-1], end=" ")
            print()
            for i in answers_data:
                if i['ID'] == final_answer.strip():
                    final_answer = i['AN']      
            print("\033[1m\033[31m???????????? :", final_answer)
            
        except KeyError:
            print('??? ????????? ?????? ????????? ????????? ?????????.')
            print(vocab)
        return final_answer

botAnswer = InputAura()

# Launch the BottlePy dev server 
import wsgiref.simple_server, os
wsgiref.simple_server.WSGIServer.allow_reuse_address = 0
if os.environ.get("PORT"):
    hostAddr = "0.0.0.0"
else:
    hostAddr = "localhost"

if __name__ == '__main__':
    bottle.run(host=hostAddr, port=int(os.environ.get("PORT", 8080)), debug=True)
    # bottle.run(host=IP, port=int(os.environ.get("PORT", 8080)), debug=True)
