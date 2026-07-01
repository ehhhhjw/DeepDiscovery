export class PaymentGateway {
	async send(amount: number): Promise<boolean> {
		// Pretend to talk to an external payment provider.
		return amount > 0
	}
}
