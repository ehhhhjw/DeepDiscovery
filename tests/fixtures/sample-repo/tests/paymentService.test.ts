import { PaymentService } from "../src/payment/paymentService"

test("charges a positive amount", async () => {
	const svc = new PaymentService()
	expect(await svc.charge(100)).toBe(true)
})
