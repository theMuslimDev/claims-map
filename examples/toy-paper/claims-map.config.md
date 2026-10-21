# Toy paper config (fixture for the tests)

```yaml
title: "Toy paper"
paper_dir: .
output_dir: out
sections:
  - {id: abstract, file: sections/00_abstract.tex, role: front}
  - {id: intro,    file: sections/01_intro.tex,    role: front}
  - {id: methods,  file: sections/02_methods.tex,  role: body}
  - {id: results,  file: sections/03_results.tex,  role: body}
terminology:
  - {id: no-Phase, pattern: '\bPhases?\b', message: 'use "stage 1/2/3", never "Phase"'}
```
