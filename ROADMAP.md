# Roadmap: planned tiles

Three sets. Each tile names the established method it is benchmarked against (the gallery's premise is
a comparison: this method versus the standard one, on real data, with one before/after figure) and its
ownership tier (hers and novel; wrapper on open tools; lab IP, needs consent). Ordering is by
novelty, clean-separability, ownership-clearability, and effort.

---

## Set 1: Calcium / imaging (extracted from the V1 bouton project)

| tile | what it is | benchmark against | tier | notes |
|---|---|---|---|---|
| **bouton-detection** | axonal bouton detection in 2-photon FOVs; blob detection plus a physiological size filter (2–9 µm) that removes shaft, dendrite, and soma artifacts | Suite2p axon ROIs · a plain LoG/DoG blob detector · SVM bouton classifiers (Bass 2017) | wrapper | the comparison is the tile: show what the size filter removes that Suite2p keeps |
| **graph-axon-reconstruction** | an axon reconstructed from its boutons as a graph, with co-firing (peak-time coincidence, amplitude-blind) as the grouping edge, plus a spatial-graph variant for contrast | plain trace-Pearson grouping (SUBPREP, Jiang 2024) · spatial nearest-neighbour | lab-IP | co-firing is the crown (amplitude-blind sibling grouping is unpublished), so lab consent precedes any public release; the graph framing and the SUBPREP comparison carry the showcase |
| **group-motion-correction** [built] | several repeat recordings of one FOV motion-corrected to a single shared reference, so one physical bouton is one ROI across repeats (across-repeat consensus) | Suite2p and NoRMCorre per-recording MC · SCOUT cross-session | wrapper | thin over the registration engine; the contribution is the workflow (concatenate, common reference, consensus) |
| **master-served-report** [built] | one self-contained HDF5 (`experiment_master.h5`) that a small REST server renders as a live interactive report (`/api/*`), with no sidecars | the Suite2p GUI · CaImAn visualisation · a static HTML dump | hers | the neat idea is that one file is the whole experiment, served live; clean-separable and clearly hers |

First picks (a suggestion): `master-served-report` (hers, cleanest to open, immediately legible) with
`bouton-detection` (wrapper, the comparison makes a strong figure) and `group-motion-correction` (wrapper). Hold
`graph-axon-reconstruction` for the lab consent; it is the scientific crown, so it graduates last by design.

---

## Set 2: RNA-seq (AD, single-cell / single-nucleus, neuron groups)

A «красива лабораторка» set. A published AD single-cell RNA-seq study is reproduced cleanly, then taken
one step deeper. The themes map onto her thesis: neuronal vulnerability by cell type, E/I balance,
disease-associated neuron states.

| tile | pattern | benchmark / step-deeper |
|---|---|---|
| **scrna-ad-reproduce** | QC, normalise, cluster, cell-type, DE (AD vs control), clean scanpy | reproduce a published AD snRNA-seq atlas; the paper's own numbers are the ground truth |
| **neuron-vulnerability** | which neuron subtypes are selectively lost or hyperactive in AD | one step past the atlas: a vulnerability score per subtype, tied to E/I markers |

### Region strategy (this is what ties the gallery to her V1 thesis)

The region is treated as a variable of the analysis. Human AD omics is richest in prefrontal and
temporal cortex (early-hit); visual (occipital) cortex is relatively spared early, which is her thesis
motif. The workhorse is PFC (ROSMAP) for the clean reproduce (best data, matched proteomics), and the
step-deeper is a PFC-versus-occipital contrast: is V1 transcriptionally spared early in AD, matching what
the calcium imaging shows. This uses the best data as the engine and the sparse occipital data as the
contrast, and turns the omics tile into her own story (calcium, RNA, protein, one V1 narrative).
Somatosensory cortex is mouse-model territory (5xFAD, THY-Tau22), whole-cortex, without a clean AD
region-match; skip it unless a mouse-model tile is wanted.

Datasets: the PFC workhorse is below. For the occipital contrast, use the ADAD frontal-plus-occipital
study (Neuron 2024, ~3k occipital nuclei) and ssREAD (a single-cell and spatial AD database with a
region breakdown, mined for occipital versus frontal).

## Set 3: Proteomics (AD, matched question)

Proteomic analysis on comparable AD data, the protein-level companion to the RNA set. Transcript and
protein diverge, and that divergence is itself the question.

| tile | pattern | benchmark / step-deeper |
|---|---|---|
| **prot-ad-reproduce** | MS proteomics QC, normalise, differential abundance (AD vs control) | reproduce a published AD brain proteomics study |
| **rna-vs-protein** | join the RNA and proteomics tiles: where do transcript and protein disagree in AD | the cross-omics step that neither single study shows, the gallery's own contribution |

---

## Candidate public datasets (curated 2026-07-21)

The unifying pick is ROSMAP. The Religious Orders Study / Memory & Aging Project carries both
single-nucleus RNA-seq and TMT proteomics from the same cohort and the same DLPFC region, so the
`rna-vs-protein` tile stands on matched data (where transcript and protein disagree in AD is the story).
Access is via the AD Knowledge Portal (Synapse).

### RNA-seq
| dataset | what | why it is a good pick | access |
|---|---|---|---|
| **Mathys et al. 2019** (ROSMAP, PFC BA10) | 80,660 nuclei, 24 AD and 24 control; the canonical AD snRNA-seq paper | reproduce-and-extend gold standard; the paper's own numbers as ground truth | Synapse `syn18485175` |
| **Mathys 2024** (ROSMAP expanded) | 2.3M nuclei, 427 participants, code on GitHub | larger and reproducible (`mathyslab7/ROSMAP_snRNAseq_PFC`) | Synapse and GitHub |
| **SEA-AD** (Allen Institute) | 4.5M cells, MTG and DLPFC, multi-modal (snRNA/ATAC/spatial) | the polished one: a data portal, thorough docs, browsable | sea-ad.org |

### Proteomics
| dataset | what | why | access |
|---|---|---|---|
| **ROSMAP TMT proteomics** (DLPFC) | protein quantification matched to the Mathys RNA cohort | matches the RNA set, so cross-omics rests on one cohort | AD Knowledge Portal (Synapse) |
| **Global brain proteome + phosphoproteome** (Bai et al., *Scientific Data* 2020) | 108 MS raw files, total and phospho, AD | published as a data descriptor, so it is well-documented and an easy entry | PRIDE (ProteomeXchange) |
| **Proteomic Atlas of the Human Brain in AD** | `PXD010603`; 9 sections × 3 AD, core proteome | suited to a regional-variance showcase | PRIDE / MassIVE |

Suggested pairing: RNA is Mathys 2019 (reproduce) then SEA-AD (the polished step-deeper); proteomics is
ROSMAP TMT (so `rna-vs-protein` sits on one cohort) with Bai 2020 (a clean data descriptor).

Sources: [Mathys 2019 (Synapse)](https://adknowledgeportal.synapse.org/Explore/Studies/DetailsPage/StudyDetails?Study=syn18485175) ·
[Mathys 2024 code](https://github.com/mathyslab7/ROSMAP_snRNAseq_PFC) ·
[Green 2023 unified atlas (Cell)](https://www.cell.com/cell/fulltext/S0092-8674(23)00973-X) ·
[Bai 2020 proteome+phospho (Scientific Data)](https://www.nature.com/articles/s41597-020-00650-8) ·
[Proteomic Atlas PXD010603](https://www.omicsdi.org/dataset/pride/PXD010603) ·
[ROSMAP omics overview](https://pmc.ncbi.nlm.nih.gov/articles/PMC11439699/)
