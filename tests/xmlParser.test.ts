import { describe, expect, it } from "vitest"
import { XMLParser } from "../src/repomap/xmlParser"

const SAMPLE_XML = `<document>
<file_summary>
This repo has a payment module.
</file_summary>
<directory_structure>
src/
  payment/
    paymentService.ts
    paymentGateway.ts
  config/
    retryConfig.ts
</directory_structure>
<file path="src/payment/paymentService.ts">
class PaymentService {}
</file>
<file path="src/config/retryConfig.ts">
export const retryConfig = { maxRetries: 3 }
</file>
</document>`

describe("XMLParser", () => {
	it("extracts file summary and all file contents when no target filter", () => {
		const result = XMLParser.extractContent(SAMPLE_XML)
		expect(result.fileSummaryContent).toContain("payment module")
		expect(result.relatedFileContents).toHaveLength(2)
	})

	it("filters file contents to target paths by basename", () => {
		const result = XMLParser.extractContent(SAMPLE_XML, ["paymentService.ts"])
		expect(result.relatedFileContents).toHaveLength(1)
		expect(result.relatedFileContents[0].path).toBe("src/payment/paymentService.ts")
	})

	it("filters directory structure to the target hierarchy", () => {
		const result = XMLParser.extractContent(SAMPLE_XML, ["retryConfig.ts"])
		expect(result.relatedDirectoryStructure).toContain("retryConfig.ts")
		expect(result.relatedDirectoryStructure).toContain("config/")
	})
})
