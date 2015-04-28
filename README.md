# s3pi

## Running tests

```bash
python setup.py test
```

## Building binary distribution

```bash
python setup.py bdist_wheel
```

## Running

### Preparation

s3pi relies on an Amazon S3 bucket for its hosting of the package index. After creating the bucket in S3, it will need to be configured to have Website Hosting enabled. The default path should be configured to index.html.

### Configuration

Before running, a configuration file needs to be created to indicate the S3 bucket and prefix being used for the python simple package index.

```ini
[default]
s3.bucket=repo.kadeem.com
s3.prefix=python/simple/
upload=true
```

### Execution

```bash
s3pi dist/
```
