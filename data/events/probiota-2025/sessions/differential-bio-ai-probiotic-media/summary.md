# Aligning HTS Data and AI for Biotech R&D: Data, Model and Probiotic Media Optimisation

## Summary
Xiangdong Zhao, who works on microbiology, and Martin Patz, who works on data and AI, of Differential Bio argued that data and AI can solve hard problems in probiotic development, if the data and the model are matched. Most laboratories today hold small datasets, under 10,000 points. That suits simple models, not complex goals such as predicting health benefits or scale-up.

Their answer is to grow data cheaply. They run fermentations in microtitre plates, using the many small wells as miniature reactors. They show what changes at that scale: oxygen transfer, shaking, air held in the plastic and the headspace, and the edge effect on outer wells. Sealing and careful set-up make each well a reliable vessel.

The case study is growth media for the probiotic strain Lactobacillus rhamnosus Gorbach-Goldin. A liquid-handling robot mixed 3,000 media formulations, and a neural network learned growth from them. It then chose 44 new recipes, tested in anaerobic tubes. The preferred plant-based recipe gave four times the cell count of standard MRS media at a lower media cost. They put the approach at about two weeks against eight to twelve by hand. These are the company's own results, presented in February 2025.

## Key takeaways
- Their three messages: data and AI have "huge potential" in probiotics development; align the dataset and the modelling approach with the goal; customise microtitre-plate screening to unlock it as a high-throughput fermentation platform (slide 28).
- Datasets today are mostly under 10,000 points and suit simple uses; microbiome impact, health benefits, single-step scale-up and process control need far more data (slide 8).
- Downscaling to microtitre plates has minimal effect at the single-cell level; the main impacts come from the high surface-to-volume ratio, which brings earlier and faster growth (slide 15).
- Sealing the plate with an airtight seal gave less than 5% variation in OD600 and pH, so each well qualifies as an independent fermentation vessel (slide 18).
- Case study method: 3,000 formulations of 10 MRS components by robot, a neural network trained on maximum OD, then 44 predicted recipes validated by CFU counts in 15 mL anaerobic tube fermentations (slide 22).
- Their result for L. rhamnosus Gorbach-Goldin: 4x higher CFU and 16% lower media cost than baseline MRS, replacing animal-based components while reusing existing ones (slide 26).

## For Vita Actives
- Relevance low: this is a methods and AI talk for probiotic producers. It touches our range only indirectly.
- My reading: cheaper, plant-based growth media would cut probiotic producers' costs, which reaches us only through a probiotic partner's pricing.
- My reading: their plant-based media used soy peptone (slide 22). Whether pea-derived peptones could serve the same purpose is an open question the deck does not raise.
- My reading: the wider point travels. The same screen-then-model loop could be put to our own process questions, if the data existed to train on (slide 27).

## Quotes
- "Data and AI have huge potential to solve complex problems in probiotics development." (slide 28)
- "Status quo is small datasets (<10k), not suitable for complex use-cases" (slide 8)
- "In-silico model is able to predict medium formula" (slide 25)

## Detail
- Results by others on the opening slide: 62% cost reduction from optimising the medium for the meat starter culture Latilactobacillus sakei (Galante et al., 2023), and 5.3x higher yield of human interferon in Pichia pastoris with machine learning (Hashizume and Ying, 2024) (slide 4).
- Mismatch costs either way: a model too large for the data cannot be trained or the problem is too difficult; a model too small reaches its capacity and cannot benefit from more data (slide 9).
- Scale trade-off: industrial and pilot runs are highly relevant to production yet costly, while microtitre plates and microfluidics grow datasets cheaply; their plan is to build a cell response model there and translate it by 3D modelling (slide 11).
- A well holds 350 µL (read from the image). Intracellular pH stayed higher in plates than in a shaking flask, which they read as better cell vitality (slide 14).
- Surface-to-volume ratio is given as 24/8 = 3 for the larger block against 6/1 = 6 for the smaller (read from the diagram); the higher ratio raises early oxygen transfer and drives earlier, higher growth (slide 15).
- Shaking has little effect early but raises cell numbers late, which they put down to falling surface tension as cells accumulate (slide 16).
- Saturating the polystyrene plate with nitrogen, or replacing the headspace air, slows growth; anaerobicity can be reached by preventing air permeability or by using oxidisers (slide 17).
- Peripheral wells suffer evaporation, temperature drift and air diffusion, which can mislead cellular assays (slide 18).
- Media components varied: glucose, soy peptone, yeast extract, sodium acetate, dipotassium phosphate, ammonium citrate, magnesium sulfate, manganese sulfate, Tween 80 and meat extract. Plate conditions were 0.5 million CFU/mL cryo-inoculation, 37 °C static incubation, airtight seal, OD read every half hour for 24 hours (slide 22).
- Model fit: R² of 0.8941 on the plant-based and cost comparisons, 0.9011 for the preferred media and 0.6631 for the tube CFU validation (read from the charts) (slide 23) (slide 24) (slide 25).
- The preferred formula is -16.3% against the MRS price line (read from the chart), and quadruples the CFU count at the higher scale (slide 24) (slide 25).
- Speed claim: HTS and model-driven work at 1x in about two weeks and cheaply, against manual and iterative work at 4x the effort over 8 to 12 weeks and costly; the model is kept as a reusable digital asset (slide 27).
- The deck carries a "© Differential Bio" footer throughout but no slide is marked "Confidential". Slides 29 to 31 are a backup section: strain screening results transfer qualitatively from plate to 2 L benchtop fermenter (slide 30), and a table of typical MRS compositions from Hayek et al., 2019 (slide 31).

## Follow-ups
- Confirm the end time and whether Nathan attended.
- Ask Differential Bio whether the media work has been published, and whether the model has since been applied beyond L. rhamnosus.
- Worth noting as a possible technology partner for fermentation-derived ingredients; a decision for Nathan.
