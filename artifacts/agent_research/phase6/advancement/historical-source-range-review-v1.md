# P1 historical-source range review v1

Qualification: **MODEL_SUBAGENT**. Authority effect: **NONE**. This is substantive model scrutiny of stored text and its permissible uses, not a qualified SourceAudit, human review, provider or isolation attestation, adoption, release acceptance, or new locator-verification result.

## Scope, method, and actual coverage

Repository root `R` below denotes exactly `/mnt/d/Code/RedChamberWorldHarness`; `R/x` denotes that absolute path. Provenance directory `P` denotes exactly `/mnt/d/Code/RedChamberWorldHarness/artifacts/agent_research/phase6/provenance`.

Read all of `R/data/provenance/sources/r4_historical.yaml` and `R/data/provenance/claims/r4_historical.yaml`. There are **12 source records in the file, of which exactly 11 historical-primary IDs are explicitly selected across ch81–100 v3 package source lists**. The twelfth is the Mao Liping secondary-study record, not an eleventh/extra selected historical-primary source. It was additionally examined below rather than silently omitted or miscounted.

Resolved all seven existing extraction manifests and outputs through `R/data/catalog/assets.index.json` read-only. Parsed their actual stored `text` fields, not merely the source-record snippets or hashes. Read the complete adjacent text ranges specified in the inventory below, including the containing law sections and named gazetteer entry. Recomputed output-file hashes against manifests (all seven match), and raw excerpt-span hashes for all 12 records (all match). These checks establish current stored-text correspondence only; no extraction rebuild or formal verifier was run.

Also read the complete already-selected C2 research narrative, integrity record, source-set, three proposed source records, three proposed claim records, transcription derivative, manifest and extraction output. Checked the C2 set/source/claim/report binding hashes and all three candidate quote spans against their actual derivative text. Inspected package source references for ch86/87/89/92/95 and the historical-ID union across all 20 packages; did **not** audit all package prose or all draft chapters.

No delegation, API, network, build, registration, catalog writes, source/claim edits, commit, or release operation. The sole intended repository write is this newly permitted report; its absence was checked before Write. Python reads used `-I` from the repository root, not a received-data directory. A PDF parser was used only to read existing secondary-study text, not execute downloaded code.

### Extraction/context inventory

All coordinates are zero-based Unicode character offsets, half-open, in the stored extraction unit; PDF physical page numbers are one-based. The context ranges below are **actual ranges read**, not a claim to have read whole books or whole source HTML pages.

| Key | Manifest and output directory under `R/corpus/extractions/` | Unit; actual substantive text read |
|---|---|---|
| A | `c1ef426fb101a99ec9d43fe19f83020f6117ae6e298f51d928e9c9e73ece50ba/` | `html:1[5400:8700]`: prison provisions before and after all three selected excerpts, including 主守教囚反異, 獄囚衣糧, 功臣應禁親人入視 and part of 鞫獄停囚待對 |
| B | `e5c179eea98317d4f4d9377f9c87763e90186e8e0d468627e9bb3679de656835/` | `html:1[2000:4600]`: multiple adjacent local offices and the complete 通州州治 entry around the prison passage |
| C | `f95f95556bdb0321f7eeb2b6fb7f358b4a95e5d441edb76d44db41faac2ffdf5/` | complete `text:1[0:956]`: derivative's provenance/reading disclaimer and all three excerpts; this is NOT a full memorial transcription |
| D | `e3a9fde9913d4c5ef3bfa93bf9b6e6507796d79aee32adb06c9c72ae17974992/` | `html:1[1600:4500]`: marriage headings, 男女婚姻 and its 条例, entire 居喪嫁娶 section and 条例, 父母囚禁嫁娶 and surrounding provisions |
| E | `e965f5c11862363d3e581b31d62a170805e72f6a4462985ba101def455c52610/` | `html:1[0:4300]`: 太妃 context, entire 皇贵妃丧仪 section, start of separate 贵妃丧仪 section |
| F | `61197a8d322c939c88c51d70a86b1f649b1243b4452cf2d4da3e7b6b7e2f59f6/` | `html:1[2500:5300]`: page metadata and complete rental article, contract date/signatures and commentary |
| G | `b82a1b24c96af90ce9e89503a249b218c1ae0cec3ddd5bac8f10c5f063e6cd20/` | complete stored `pdf:page:7[0:795]`, including the excerpt's methodological lead-in and unfinished next-page sentence |

In every directory above, the exact manifest filename is `manifest.json` and the exact registered output filename is `units.jsonl`; the directory mapping plus unit/range identifies the actual context precisely. All paths are rooted at the absolute `R` above. The corresponding output SHA256 values are, in A–G order:

- A `360e1997471f23344b6218bfb240d8d622623b4b4a087f541c9dc9db2e4baf98`
- B `6ba3bb6650e6ac6cb03130d3c33d9fb12fb1326fed4567b8e0e22204ced2554f`
- C `999effc20a431c68d28b9378eee31ce492e9a57e9b985f25ff2a7388adf9c11c`
- D `6f825052070cb8862304edc2f59e275bd524158ecbd97941ea52a1e7e5eb48b4`
- E `9ca233aedb48b328af4e072d409b29e9cef70b63cee689ea5cc0c9949e7e8278`
- F `44977b3557cf6ec3d400a1311f98bf03ac97b4331cd00f0293511a7c5380110d`
- G `d416305d83f99e69362cf4f931a61696d05b2000860c3b56f987dafb932ef10c`

### Unread facsimiles and remaining fidelity limits

**No historical manuscript, law-book image, gazetteer facsimile, or rental-contract image was newly opened or visually collated in this continuation.** No original NPM005664 image/PDF was newly read. The C2 narrative describes earlier model visual readings; reading that narrative here does not repeat or independently verify those readings. The 1975 book, its copyright page, the 130-page electronic reprint, and its source edition were not newly examined. Modern web transcription/extraction fidelity to original printed pages is not established by the exact matches above.

For the secondary paper only, additionally read the existing PDF's text layer on physical pages **1–6 and 8** (stored extraction already supplies page7), covering printed pages3–10; no page-image inspection and no full-article read. PDF path: `R/sources/primary/received/6a296fa7157747efa8d4f61dba01279d23daea28d7dd284bc4c5a5993f007826/mao2013.pdf`.

## Eleven selected historical-primary findings

“Supported within stored text” below means the stated narrow proposition is present in the examined carrier, not fresh historical authentication. Downstream chapter numbers refer to actual selected package references, not a full narrative audit.

### 1. Outsider access

**ID:** `src:history:daqinglu:v36:outsider-access`  
**Exact quote / locator:** A, `html:1[6371:6407]`:

> 若〈獄官典卒〉容縱外人入獄及〈與囚𫝊通言語〉走泄事情於囚罪無增減者笞五十

**Context:** 主守教囚反異 concerns officials/guards helping alter an established case or communicate case information; the preceding sentence treats increased/decreased guilt more severely, and the following sentence addresses bribery. Its 条例 separately punish unauthorized entry by clerks, runners and officials' household servants. This is not a context-free ban on all contact of every kind.

**Narrow support:** the code penalizes custodians allowing outsiders in and communicating/leaking matters to prisoners, including the stated case where guilt is not increased/decreased. **Interpretation:** a prison visit requires an institutional channel rather than frictionless private access. **Overclaim:** no visit, message, or privileged exception is ever possible; every conversation has one identical penalty; Xiaohong must use a particular bribe/person/route.

**Date/jurisdiction/wording limits:** stored 四库全书本 Qing code; the examined provisions do not individually date their enactment or prove implementation in a particular fictional year. Embedded 〈〉 annotations are a distinct explanatory layer, not punctuation to discard silently. Central 刑部-entry 条例 should not be generalized into identical layouts/procedures for every local jail.

**Downstream:** ch92; `claim:history:h01:controlled-access` can support regulated access, not a recovered rescue scene. Read jointly with item2, not as an absolute prohibition.

### 2. Relative visits and food delivery

**ID:** `src:history:daqinglu:v36:relative-visits`  
**Exact quote / locator:** A, `html:1[7277:7368]`:

> 一在監人犯許令祖父母父母伯叔兄弟妻妾子孫一月兩次入視使役之人不越兩名若有送飲食者提牢官騐明禁子轉送其盜犯妻子家口不許放入監門探視違者妻子家口枷號兩個月責四十板不准收贖提牢司獄官吏叅處

**Context:** 獄囚衣糧 first imposes duties to seek food, medicine and, for critical illness, family access; the following 条例 regulate rations, medical personnel and prison abuses. Later 功臣應禁親人入視 gives a separate rule for meritorious officials and officials of fifth rank or above. Thus this is a differentiated legal setting, not one universal rule without exceptions.

**Narrow support:** listed kin may enter twice monthly; serving persons are limited to two; food is checked by the 提牢官 and passed by 禁子; the excerpt expressly excludes 盜犯妻子家口 from entering the prison gate to visit. **Interpretation:** kin, authorized attendants and intermediated delivery are distinct possible channels. **Overclaim:** “旧仆当然探监权,” unrestricted entry, guaranteed food arrival, or a blanket inability of any servant ever to participate. The positive phrase 使役之人 must not be suppressed merely because it does not establish a former servant's independent entitlement.

**Limits:** same compilation/date caveat as item1. Kin category, prisoner category, attendant status and institution must be established before applying a particular rule. “一月兩次” is not evidence of a selected character's actual visitation calendar.

**Downstream:** ch92; narrows `claim:history:h01:controlled-access`. A mechanically plausible controlled-delivery channel does not establish who actually visits Bao Yu.

### 3. Waiting for questioning

**ID:** `src:history:daqinglu:v36:waiting-for-questioning`  
**Exact quote / locator:** A, `html:1[7469:7520]`:

> 一五城司坊羈禁人犯及刑部等衙門發交各司坊枷號及看守牽連待質等犯果係赤貧並無家屬送飯者每人每日給老米一升

**Context:** the sentence continues **按季造報户部核銷**; its immediate purpose is ration accounting for specified detainees. Adjacent 鞫獄停囚待對 discusses inter-office production of co-accused for confrontation; its three-day dispatch rule and separate capital-case processing language are not the duration of this selected detainee's custody.

**Narrow support:** 五城司坊/刑部-related custody includes the category 牽連待質; indigent detainees without family food receive a stated ration. **Interpretation:** a person may be held pending evidentiary confrontation rather than already serving a final sentence. **Overclaim:** this clause is a general authorization to detain anyone indefinitely; Bao Yu's charge, guilt, jail, number of days, ration actually received or release deadline follows from it.

**Limits:** visibly capital-administration institutions, not a proven universal county practice; compilation enactment dates and compliance not verified. “牽連待質” should not be silently treated as an exact synonym for every modern “候问” procedure.

**Downstream:** ch92; `claim:history:h01:waiting-for-questioning` is useful as a narrow category/mechanism, not a narrative clock.

### 4. Prison-god shrine: specifically Tongzhou

**ID:** `src:history:shuntianfu:prison-god`  
**Exact quote / locator:** B, `html:1[3434:3500]`:

> 监狱在大门内西向。旧分内外二监，乾隆三十年，知州万廷兰将外监归并内监，现在囚房六间，女囚房一间，狱神庙一间，禁卒房一间，更夫房一间。

**Context locator and correction of vagueness:** the containing entry begins **通州州治** at B[3278], not an unspecified Qing jail. The immediately following 库房 paragraph starts at3500. It records earlier earthquakes and successive repairs; neighboring Yongqing, Dong'an, Xianghe and Sanhe entries describe different office arrangements.

**Narrow support:** the 光绪 gazetteer transcription attributes one 狱神庙 room to this Tongzhou state-office prison description. **Interpretation:** such a shrine can be a historically plausible local prison space. **Overclaim:** every prison has one, every shrine has the same social function, or this supplies the exact room/route/encounter in a lost novel scene.

**Date/jurisdiction limits:** late-Qing gazetteer compilation with retrospective repairs; **乾隆三十年** dates the merging of the outer/inner prisons, not explicitly the shrine's construction. “现在” belongs to the gazetteer's account, not automatically to Qianlong30 or a fictional early-Qing year. Tongzhou is not simply an interchangeable 刑部 prison.

**Downstream:** ch92; `claim:history:h01:prison-god-space` is bounded feasibility only. Context now supplies a more exact locality than the source note's generic “部分地方监狱.”

### 5. Inventory and sealing

**ID:** `src:history:cao:1728:inventory-seal`  
**Exact quote / locator:** C, `text:1[810:844]`:

> 總督范時繹已將曹頫家管事數人拿去夾訊監禁所有房產什物一併查清造冊封固

**Context:** complete stored C text is a **three-local-excerpt model transcription v2**, expressly not museum transcription, OCR, or independent human review. It names NPM005664 and labels286 an unconfirmed imported number. It does not contain the full preceding/following memorial clauses.

**Narrow support:** the derivative reports Fan Shiyi having household managers interrogated/imprisoned and property/items inventoried and sealed. **Interpretation:** this historical case is a close administrative analogy for confiscation mechanics. **Overclaim:** all family members were imprisoned, every property item was confiscated or sold, every seizure follows this exact sequence, or Jia-family officials/documents/actions are recovered facts.

**Limits:** attributed memorial date 雍正六年三月初二日 (1728 year identification only; no fresh calendar conversion), Jiangning/Cao case reported to the emperor, not a nationwide universal procedural rule. “已” is retrospective reporting, not an independently checked execution record. Old CAO-ARCHIVE-286 edition identity is separate from NPM005664 attribution and remains unresolved here.

**Downstream:** ch89; `claim:history:h02:inventory-sealing` may be used as reported-case feasibility with the transcription and identity caveats. Newly selected C2 candidate does not supersede this old ID.

### 6. Pawn tickets: count is not duration or cashflow

**ID:** `src:history:cao:1728:pawn-tickets`  
**Exact quote / locator:** C, `text:1[859:892]`:

> 餘則桌椅床杌舊衣裳零星等件及當票百餘張外並無別項與總督所查冊內彷彿

**Context:** the same limited three-excerpt derivative; “餘則” and “與總督所查冊內彷彿” place the report in an inventory/comparison setting, but the full accounting before it is absent from C. The furniture and old clothing are mentioned as remaining items alongside tickets; they are not identified as the pledged goods underlying each ticket.

**Narrow support:** the report says there were **more than one hundred pawn tickets**, with remaining items and an approximate comparison to the governor-general's inventory. **Interpretation:** pawning was involved in this household's material circumstances. **Overclaim:** ticket count establishes long-term or continuous pawning, dependable cashflow, dates/frequency, sums, redemption, particular pledged objects, causes of decline, or the fictional household's pawn schedule.

**Material adverse finding:** the source's note says **“长期典当作为现金流机制”**, and `claim:history:h05:pawn-as-cashflow` is currently DIRECT_ASSERTION/SUPPORTED with **“持续典当作为现金流工具”**. The examined excerpt does **not** directly establish duration or cashflow use. Those parts are an inference at best, and become overclaim when presented as firm facts. This report does not borrow their existing SUPPORTED status or edit them. The C2 candidate claim is appropriately narrower: only that the memorial reports the tickets.

**Limits:** same 1728 attributed case/derivative/old286 caveats as item5. Preserve **床杌、舊衣裳**; the C2 report records variants 床几、旧衣 in an unconfirmed electronic reprint, not interchangeable raw wording.

**Downstream:** ch86,95. Pawn tickets can motivate an explicitly analogical resource question; they cannot settle an ongoing income stream, treatment budget, winter supplies or fictional possessions.

### 7. Family housing: planned allocation is not completed delivery

**ID:** `src:history:cao:1728:family-housing`  
**Exact quote / locator:** C, `text:1[909:955]`:

> 至曹頫家屬蒙恩諭少留房產以資養贍今其家屬不久回京奴才應將在京房屋人口酌量撥給以彰聖主覆載之恩

**Context:** the third excerpt of the same derivative, not a final allocation list. **蒙恩諭少留房產** reports an imperial instruction; **不久回京** and **應將…酌量撥給** describe prospective arrangements.

**Narrow support:** the memorial reports an instruction to leave limited property for maintenance and envisages discretionary allocation of Beijing houses/personnel upon the family's return. **Interpretation:** confiscation need not imply total elimination of every possible support resource. **Overclaim:** a particular house/person was actually handed over, a settled amount/ownership/tenancy is documented, stable long-term support was guaranteed, or a Jia-family household has this exact accommodation.

**Limits:** attributed 1728 memorial moving from Jiangning toward Beijing; administrative grace/discretion in this case, not a general entitlement. **房產** is not silently replaceable with 房屋; **人口** is not proof of which individual servant accompanied whom. Old286 and original-image fidelity limitations remain separate.

**Downstream:** ch87,89,95; `claim:history:h04:post-confiscation-housing` remains usable only at its “可能/少留或酌拨” level, not as proof of completed housing.

### 8. Mourning and marriage

**ID:** `src:history:daqinglu:v10:mourning-marriage`  
**Exact quote / locator:** D, `html:1[3098:3275]`:

> 凡〈男女〉居父母及〈妻妾居〉夫喪而身自〈主婚〉嫁娶者杖一百若〈男子〉居〈父母〉喪〈而〉娶妾妻〈居夫喪〉女〈居父母喪而〉嫁人為妾者各減二等若命婦夫亡〈雖滿服〉再嫁者罪亦如之〈亦如凡婦居喪嫁人者懝斷〉追奪〈勅誥〉並離異知〈係居喪及命婦〉而共為婚姻者〈主婚人〉各減五等〈財禮入官〉不知者不坐〈仍離異追財禮〉若居祖父母伯叔父母姑兄姊喪〈除承重孫外〉而嫁娶者杖八十

**Context:** selected quote stops before **〈不離異〉妾不坐**. The remainder distinguishes acting as marriage arranger during specified mourning, coerced remarriage of a widow wishing to remain chaste, and further 条例. Adjacent **父母囚禁嫁娶** separately distinguishes marrying on one's own from marrying under the imprisoned parents'/grandparents' command and limits banqueting. Applying marriage law here requires more than one cherry-picked clause.

**Narrow support:** the code prescribes differentiated sanctions for specified kin/spousal mourning and marriage roles. **Interpretation:** mourning is a consequential constraint requiring investigation in a proposed marriage sequence. **Overclaim:** every bereavement creates the same ban, every violation entails divorce, or parents' mourning rules mechanically determine a consort-relative's timetable.

**Limits:** compilation-specific Qing text, unverified individual enactment dates/implementation; parent, spouse, grandparent, collateral kin, title-holding widow and arranging party are not identical categories. The text does not identify Yuanfei's rank, each character's legal mourning relation or any actual marriage date. **No real or uniquely recoverable Bao Yu–Bao Chai marriage date is asserted.**

**Downstream:** ch87; `claim:history:h03:mourning-constrains-marriage` is defensible as a legal-text constraint, not proof of uniform actual compliance or a calendar result. Read with item9 without combining unlike periods into one invented deadline.

### 9. Imperial noble consort mourning: a dated case with several clocks

**ID:** `src:history:huidian:v89:huangguifei-mourning`  
**Exact quote / locator:** E, `html:1[1673:1692]`:

> 姻戚人等成服，皆大祭日除服，百日剃头。

**Context locator:** **一、皇贵妃丧仪** begins at E[1568]; the whole section continues to E[3882], where the distinct **一、贵妃丧仪** begins. It opens with **雍正三年十一月二十三日，敦肃皇贵妃薨**. Adjacent groups have differing rules: the born imperial son has二十七日除服/百日剃头; some appointed officials大祭日除服/剃头; other attendants大祭日除服/百日剃头. Subsequent sacrifices, anniversary rites and transfer/burial extend across later years.

**Narrow support:** in this recorded imperial-noble-consort ritual case, affinal relations dress in mourning, remove it on the great-sacrifice day, and shave at100 days. **Interpretation:** court-affinal mourning has a differentiated ritual regime and cannot simply be equated with private parental mourning. **Overclaim:** “百日” is explicitly a wedding prohibition/permission date; 大祭 necessarily equals day100; robe removal, hair cutting and burial are one clock; the case establishes a universal identical marriage rule for every consort's relatives.

**Limits:** memorialized court ritual, dated case 雍正三年 and later precedents, not a household marriage statute. 皇贵妃 and 贵妃 are visibly separate headings; matching the novel's consort rank and family status would require independent evidence. No calendrical conversion or factual marriage-date conclusion is supplied.

**Downstream:** ch87; `claim:history:h03:consort-special-rites` is supported within the compendium at the narrow ritual level. It does not complete a chronology solver.

### 10. Marriage authority: kin framework, not a negotiated scene

**ID:** `src:history:daqinglu:v10:marriage-authority`  
**Exact quote / locator:** D, `html:1[2443:2468]`:

> 一嫁娶皆由祖父母父母主婚祖父母父母俱無者從餘親主婚

**Context:** the same 条例 immediately continues **其夫亡攜女適人者其女從母主婚若已定婚未及成親而男女或有身故者不追財禮**. The earlier 男女婚姻 text concerns disclosure, marriage documents, betrothal gifts, repudiation and competing arrangements, including a child away from home who has independently married. Thus the framework has defined circumstances, not a sufficient script for every conflict.

**Narrow support:** marriage is normatively arranged by grandparents/parents, otherwise other kin; the following clause explicitly preserves maternal authority in a specified remarriage situation. **Interpretation:** kin authorization remains a mechanism to be dramatized rather than erased. **Overclaim:** the excerpt supplies a complete priority ranking between living grandparent and parent, excludes all maternal kin/women, identifies who actually wins a household argument, or provides Jia Mu/Wang Furen/Xue Yima's specific consent.

**Limits:** same compilation-specific enactment/compliance caveat; household genealogy, survival/availability, marital status and prior betrothal must be independently established. Authority wording does not independently supply a marriage date or displace the restrictions in item8.

**Downstream:** ch87,89,95; `claim:history:h04:senior-kin-marriage` can support a general normative framework, not a reconstructed conversation or fictional decision.

### 11. Rental contract: temple shop premises, not a residential price index

**ID:** `src:history:beijing:1774:rental-contract`  
**Exact quote / locator:** F, `html:1[3760:3879]`:

> 立租契人系瑞应寺下院当家宗玉，今有二拔子庙上铺面房屋一所，共计十六间，今租沙河德春店作理生意，连借缸三口。对众言定每年租价清钱五十千正，只许客辞主，不许主辞客。房屋损坏，房主修理。恐后无凭，立租帖存照。现收租价清钱三十千正。租价不许增长。

**Context:** complete article identifies a temple-held commercial lease, not domestic accommodation. It immediately supplies **乾隆三十九年六月初六日**, the monk's signature and witnesses. Modern webpage date is **2020年01月21日**, not the contract date. Commentary locates Shahe/Erbozi in present Changping but explicitly says Ruiying Temple's precise position **有待考证**. It describes this as the one temple-archive contract in its collection leasing shopfronts to merchants; it does not claim representativeness across Beijing housing.

**Narrow support:** a written 1774 lease for16 rooms used by a shop specifies annual rent清钱五十千, current receipt三十千, three borrowed jars, landlord repairs, tenant-protective termination and no rent increase. **Interpretation:** rental arrangements can impose recurring obligations and involve explicit negotiated terms. **Overclaim:** every lease has those terms; current receipt equals full annual rent; the difference is proven arrears; period length, exchange rate, residential courtyard layout, Jia-family rent or affordability follows from this contract.

**Limits:** Qianlong39/1774, local temple commercial property, modern institutional webpage transcription; original contract image not newly checked. Preserve the transcription's **二拔子** in the quote even though commentary uses二拨子; do not normalize silently. No conversion of清钱五十千 to silver or modern money is supported here.

**Downstream:** ch86,87,89,95; `claim:history:h04:rental-mechanism` and `claim:history:h05:rental-cost` are analogical mechanisms. The annual term supports recurrence for this contract, not a fictional tenant's actual ongoing liability or a representative market rent.

## Additional secondary record: read, but not in the eleven-ID selected union

**ID:** `src:research:mao-liping:2013:natal-family`  
**Exact stored quote / locator:** G, `pdf:page:7[554:669]`, physical PDF7 / printed9; line breaks retained:

> 親情使得娘家與出嫁女仍保持密切往
> 來，稍有餘力的娘家會對生活貧困的女兒女婿予以接濟；反
> 之，若娘家貧困，女兒亦千方百計進行救助－以女性為紐
> 帶的姻親關係同樣是下層家庭的主要社會關係。另一方面，
> 下層社會姻親之間的彼此救助頗具局限性

The full stored page preceding this passage explains unstable/multiple occupations, tenant farming versus wage labor, small-scale trade and use of submitted contracts alongside pleadings/testimony/judgments. Its final sentence continues onto physical8 / printed10: many natal families themselves struggle for subsistence, assistance may be unaffordable, and in-laws may fear property leakage or discourage contact. Reading that continuation prevents turning the positive half into automatic adequate support.

Additional actual text-layer reading confirms the abstract's **124 Sichuan Nanbu county cases**, selected from the ritual office's women-centered cases, not a random sample of all Qing marriages. Physical5 / printed7 says over90% of the surviving county archive is post-Daoguang and female-centered pre-Jiaqing cases were almost unavailable. Its selected case table is Jiaqing8, Daoguang25, Xianfeng18, Tongzhi34, Guangxu39. Therefore its center of gravity is nineteenth-century lower-status litigating families, not early-eighteenth-century metropolitan aristocrats. Litigation/survival and class selection limit representativeness; pleadings can be interested assertions, and the paper's interpretation is not identical with every underlying court finding. Physical2 also cites received-novel ch81; that citation is not independent evidence for a lost original continuation.

**Narrow support:** the secondary author argues for continued natal links, sometimes reciprocal limited aid, and resource-constrained kin relations in the studied material. **Interpretation:** natal ties may be a possible channel of support or intervention. **Overclaim:** a universal, enforceable, fixed or sufficient natal-family allowance; a named aristocratic woman's particular income/home/supplies; immediate transfer from these samples to the novel's time/place/class. Relevant graph claims are `claim:history:h06:natal-family-ties` and `claim:history:h06:aid-is-limited`; no explicit ch81–100 v3 package source-list selection of this ID was found. This paragraph is supplemental context, not a fabricated twelfth selected-source dependency.

## C2 selected research: same words, distinct lineage and unresolved fidelity

### Records actually read and bindings checked

The four packages **86/87/89/95** explicitly select:

- `P/research-source-set-npm005664-c2-v1.json`, SHA256 `c8576fef93d314a57e63d4cdcff24d415d27b65bef6aad52b7677139a0ca3ff3`.
- Its bound sources `P/proposed-npm005664-sources-20261014.json`, SHA256 `d065cd412e85cadc1ba1eb2dc79718db1691d55515d4079d41e4ebf64130ac55`.
- Its bound claims `P/proposed-npm005664-claims-20261014.json`, SHA256 `0d4bd9e3da721a347f85d2948233d42253dd8f88b782120b1679f7fc9fe777c5`.
- Its reading narrative `P/c2-cao286-npm005664-research-20261014.txt`, SHA256 `ec1c4e06e9093fcad665505b58e9d392ba025cd492cd60f1cc3a41c7b58f1868`.

Also read `P/c2-research-integrity-20261014.json`; its historical network/original-preservation observations are **reported prior observations**, not actions repeated by this continuation.

Actual candidate text/extraction files read:

- `P/proposed-npm005664-model-transcription-20261014.txt` → `7f1ec76956cffe3e59e45d2cce3452e0726f3c883c9157358f59bea7ae34bb9d`.
- `P/proposed-npm005664-extraction-manifest-20261014.json` → `7117a36e0c73cc134c64b59a7a00059b90097d6d4df9953f4a1d93ad2ec7229c`.
- `P/proposed-npm005664-extraction-units-20261014.txt` → `b2bdba434989e5749093be4154bc143deae5b52b8e0c5743bb8d970b4e48aaf6`.

All three current hashes equal their cited refs, but none of these three asset IDs is in the current catalog index; the selected set's `asset_bindings` is empty. This is a resolution caveat, not a new loader/gate result. No registration was attempted.

### Three proposed sources and claims

All three candidate quotations are exactly the same raw wording as items5–7, with different derivative locators:

| Candidate source ID | Actual C2 unit span | Same exact quote as | Bound original-image location, as recorded (not newly viewed) |
|---|---|---|---|
| `src:history:npm005664:1728:inventory-seal` | `text:1[1074:1108]` | item5 | Wang, figure5, PDF physical4 / printed59, xref22 |
| `src:history:npm005664:1728:pawn-tickets` | `text:1[1334:1367]` | item6 | same figure/page/image as inventory |
| `src:history:npm005664:1728:family-housing` | `text:1[1597:1643]` | item7 | Zheng, figure19, PDF physical15 / printed82, xref112 |

The recorded Wang PDF SHA is `5791f0fee06af35e1f5d98c0ab4f06a7c088f818f5597b4eab6f30bd519327fa`; image SHA `5e7bda189619a35403a6619f01c14fe6bde67af05c957b169168a811f477ce20`. Recorded Zheng PDF SHA is `1798f0451e35b8383c48661fd4fe9fc94c97ba67b281498dc6a5a36ecd6d1314`; housing image SHA `fc9f25b3951d3d8322079944a499e1130ba9b94053a4c8f3b46e8f8ee468e3c7`. These identify recorded targets only; this report did not reopen them.

Matching proposed claim IDs are `claim:history:npm005664:1728:inventory-seal`, `claim:history:npm005664:1728:pawn-tickets`, and `claim:history:npm005664:1728:family-housing`. Each remains **NOT_ESTABLISHED**, **TRANSCRIPT_WEAK**, **review_status=PENDING**, authority **HISTORICAL_FEASIBILITY/NONE**. Proposed source locators remain **UNVERIFIED**, facsimile bindings **MODEL_READING_PENDING**. Their narrow wording respectively says the memorial reports inventory/sealing; reports more than100 tickets; and reports an instruction plus proposed discretionary housing/personnel allocation. Nothing here upgrades those states.

### What the C2 narrative does and does not establish for this reading

The prior narrative reports official NPM catalog attribution to 隋赫德, the reign date, size and馆藏005664, and model image-reading observations in two official2024 reproductions. **Two reproductions of one memorial remain one historical witness**. Their appearance in a second paper, matching hashes, or another derivative transcription is not another independent archival event or human review.

The narrative distinguishes a published bibliographic citation for the **1975年3月中华书局第1版《关于江宁织造曹家档案史料》** from the unconfirmed **130-physical-page electronic reprint**, whose entry286 occurs on its physical121 with self-made footer. It explicitly lacks a copyright-page/source-edition chain and authoritative **286 = NPM005664** concordance. The reported title/date/long textual agreement supports a candidate correspondence, not a closed identity bridge.286 is not demonstrated to be an old archive number, paper page286, or confirmed1975 item number.

The report also records electronic-reading differences **床几/床杌、旧衣/舊衣裳、140/114** and a secondary quotation's **房屋/房產** difference. This continuation newly verifies none of those manuscript readings or numbers. They show why exact derivative span matching cannot authenticate original-image fidelity or silently merge old and new lineage. The number issue is outside the three selected quotes and is not promoted into a new historical claim here.

Existing old-record `locator_verification.status=VERIFIED` is a current repository fact, not proof supplied by this continuation of a confirmed1975 lineage, original-image reading accuracy, qualified human review, sustained cashflow, completed housing allocation, or narrative events. Prior PENDING/FAIL observations reported by C2 are not erased, and no new PASS is issued.

## Disposition and downstream limits

1. **All eleven selected historical-primary records received actual adjacent stored-text scrutiny**, not a hash/excerpt-only pass; the extra secondary record and selected C2 source/claim/report records were also read with explicit scope distinctions.
2. Important positive contextual findings: the shrine is specifically **Tongzhou**, the prison-visit rule includes **使役之人** and a theft-family exclusion, the “待质” passage is a capital-institution **ration** clause, imperial ritual distinguishes **除服/剃头** clocks and consort ranks, and the rental article is explicitly about **temple commercial premises** with its exact temple site still uncertain.
3. Most consequential adverse semantic finding: **百余张当票 does not directly establish 长期/持续典当 or cashflow**. Existing source-note/claim wording is stronger than the examined text. Housing wording is prospective/discretionary; a completed allocation is not established.
4. Marriage rules and court ritual constrain categories and possible sequences, but do not determine a real or uniquely recovered marriage date. Kin authority is a normative framework, not proof of which fictional elder consented or what was said.
5. C2 improves inspectability of a candidate NPM005664 lineage but remains a model/PENDING derivative lane with unresolved old286 mapping and unregistered derivative refs. **Original-image fidelity was not newly verified.**
6. Historical/legal/secondary feasibility is not narrative fact, transcription exactness is not historical authentication, and a useful research finding is not release/source admission. No claim to a full draft audit, full historical-carrier read, independent facsimile collation, formal closure, human qualification, provider attestation or isolation certification is made.
