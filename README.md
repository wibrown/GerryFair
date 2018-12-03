# Rich Subgroup Fairness

This repository contains python code for both 
* learning fair classifiers subject to the fairness definitions in https://arxiv.org/abs/1711.05144
* auditing standard classifiers from sklearn for unfairness
* fairness sensitive datasets for experiments https://arxiv.org/abs/1808.08166

### Prerequisites

python packages: pandas, numpy, sklearn, matplotlib

## Using our package

Please see our [jupyter noteboook](./GerryFair&#32;Demo.ipynb)


## Datasets
#### communities: http://archive.ics.uci.edu/ml/datasets/communities+and+crime
#### lawschool: https://eric.ed.gov/?id=ED469370
#### adult: https://archive.ics.uci.edu/ml/datasets/adult
#### student: https://archive.ics.uci.edu/ml/datasets/student+performance (math grades)


## License
* Maintained by: Seth Neel (sethneel@wharton.upenn.edu)
* Property of: Michael Kearns, Seth Neel, Aaron Roth, Z. Steven Wu.

## Acknowledgments

* Thank you to the authors of: http://fatml.mysociety.org/media/documents/reductions_approach_to_fair_classification.pdf, whose algorithm/code is in the `fairlearn` folder, and is audited in `Audit.py`.
