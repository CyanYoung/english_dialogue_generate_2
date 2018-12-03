from keras.layers import Conv1D, GlobalMaxPooling1D
from keras.layers import Dense, Dropout, Concatenate, RepeatVector

import keras.backend as K
from keras.engine.topology import Layer


win_len = 5
seq_len = 100


def s2s_encode(x1):
    ca = Conv1D(filters=128, kernel_size=win_len, padding='valid', activation='relu', name='encode1')
    mp = GlobalMaxPooling1D()
    da = Dense(200, activation='relu', name='encode2')
    h1 = ca(x1)
    h1_n = mp(h1)
    return da(h1_n)


def s2s_decode(x2, h1_n, vocab_num):
    ca = Conv1D(filters=128, kernel_size=win_len, padding='valid', activation='relu', name='decode')
    da = Dense(vocab_num, activation='softmax', name='classify')
    buf_len = seq_len + win_len - 1
    h1_n = RepeatVector(buf_len)(h1_n)
    h2 = Concatenate()([x2, h1_n])
    h2 = ca(h2)
    h2 = Dropout(0.2)(h2)
    return da(h2)


def s2s(embed_input1, embed_input2, vocab_num):
    h1_n = s2s_encode(embed_input1)
    return s2s_decode(embed_input2, h1_n, vocab_num)


class Attend(Layer):
    def __init__(self, unit, **kwargs):
        self.unit = unit
        super(Attend, self).__init__(**kwargs)

    def build(self, input_shape):
        assert isinstance(input_shape, list)
        self.seq_len = input_shape[0][1]
        self.embed_len = input_shape[0][2]
        self.w = self.add_weight(name='w', shape=(self.embed_len * 2, self.unit),
                                 initializer='glorot_uniform')
        self.b1 = self.add_weight(name='b1', shape=(self.unit,),
                                  initializer='zeros')
        self.v = self.add_weight(name='v', shape=(self.unit, 1),
                                 initializer='glorot_uniform')
        self.b2 = self.add_weight(name='b2', shape=(1,), initializer='zeros')
        super(Attend, self).build(input_shape)

    def call(self, x):
        assert isinstance(x, list)
        h1, h2 = x
        c = list()
        for i in range(self.seq_len):
            h2_i = K.repeat(h2[:, i, :], self.seq_len)
            x = K.concatenate([h1, h2_i])
            p = K.tanh(K.dot(x, self.w) + self.b1)
            p = K.softmax(K.dot(p, self.v) + self.b2)
            p = K.squeeze(p, axis=-1)
            p = K.repeat(p, self.embed_len)
            p = K.permute_dimensions(p, (0, 2, 1))
            c_i = K.sum(p * h1, axis=1, keepdims=True)
            c.append(c_i)
        return K.concatenate(c, axis=1)

    def compute_output_shape(self, input_shape):
        assert isinstance(input_shape, list)
        return input_shape[0]


def att_encode(x1):
    ca = Conv1D(filters=128, kernel_size=win_len, padding='valid', activation='relu', name='encode1')
    da = Dense(200, activation='relu', name='encode2')
    h1 = ca(x1)
    return da(h1)


def att_decode(x2, h1, vocab_num):
    ca = Conv1D(filters=128, kernel_size=win_len, padding='valid', activation='relu', name='decode1')
    da1 = Dense(200, activation='relu', name='decode2')
    attend = Attend(200, name='attend')
    da2 = Dense(vocab_num, activation='softmax', name='classify')
    h2 = ca(x2)
    h2 = da1(h2)
    c = attend([h1, h2])
    s2 = Concatenate()([h2, c])
    s2 = Dropout(0.2)(s2)
    return da2(s2)


def att(embed_input1, embed_input2, vocab_num):
    h1 = att_encode(embed_input1)
    return att_decode(embed_input2, h1, vocab_num)
