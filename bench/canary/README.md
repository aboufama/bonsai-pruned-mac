# Canary: an instant check that an edit broke nothing else

50 short questions with one exact expected answer each, in seven skills: arithmetic, following a format, code, tool calls, language, reading and general knowledge.

It is scored without generating text. The expected answer is appended to the prompt and the model's probabilities are read off: `tf_exact` is the share of questions where every answer token is the model's top choice, and `nll` is the average negative log-probability per answer token. One short forward pass per question, a few seconds for all 50.

Use it after every candidate edit (`lab.canary(model)` in the weight lab). It is a tripwire, not a benchmark: it shows a collapse immediately, and anything it flags should be confirmed on the real benchmarks. For this project, losses in `knowledge` are acceptable; losses in `tool`, `format` and `reading` are not.

The questions were written for this project and are not taken from any dataset.
