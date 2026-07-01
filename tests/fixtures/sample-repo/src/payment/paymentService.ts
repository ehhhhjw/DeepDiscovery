import { retryConfig } from "../config/retryConfig"
import { PaymentGateway } from "./paymentGateway"

export class PaymentService {
	private gateway = new PaymentGateway()

	async charge(amount: number): Promise<boolean> {
		let attempts = 0
		while (attempts < retryConfig.maxRetries) {
			const ok = await this.gateway.send(amount)
			if (ok) {
				return true
			}
			attempts++
		}
		return false
	}
}
