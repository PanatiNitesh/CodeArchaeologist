import os
import shutil
import git
import time
from datetime import datetime
from pathlib import Path

SAMPLE_REPO_DIR = Path(__file__).resolve().parent.parent.parent / "sample_repos" / "enterprise_ecommerce"

def create_sample_repository(target_dir: Path = None) -> str:
    """
    Creates an authentic Git repository with complete 2022-2026 evolution history,
    multi-tier architecture (Controllers, Services, Repositories, Models, Tests),
    and historical commits for immediate out-of-the-box demonstration of CodeArchaeologist.
    """
    repo_path = target_dir or SAMPLE_REPO_DIR
    if (repo_path / ".git").exists():
        return str(repo_path)

    if repo_path.exists():
        shutil.rmtree(repo_path, ignore_errors=True)

    repo_path.mkdir(parents=True, exist_ok=True)
    repo = git.Repo.init(repo_path)

    # Helper to commit with custom author and timestamp
    def commit_with_date(msg: str, date_str: str, author_name: str = "Elena Rostova", author_email: str = "elena@archaeo.io"):
        author = git.Actor(author_name, author_email)
        repo.git.add(A=True)
        # Set commit date
        os.environ["GIT_AUTHOR_DATE"] = date_str
        os.environ["GIT_COMMITTER_DATE"] = date_str
        repo.index.commit(msg, author=author, committer=author)

    # 1. 2022-03-15: Initial commit & repository structure
    readme_content = """# NovaCommerce Engine

AI-powered modern commerce and legacy service suite.
Architecture consists of API Controllers, Domain Services, Database Repositories, and Caching Layers.
"""
    (repo_path / "README.md").write_text(readme_content, encoding="utf-8")
    
    src_dir = repo_path / "src"
    (src_dir / "auth").mkdir(parents=True, exist_ok=True)
    (src_dir / "users").mkdir(parents=True, exist_ok=True)
    (src_dir / "payment").mkdir(parents=True, exist_ok=True)
    (src_dir / "orders").mkdir(parents=True, exist_ok=True)
    (src_dir / "common").mkdir(parents=True, exist_ok=True)
    (src_dir / "tests").mkdir(parents=True, exist_ok=True)

    # 2022-04-10: Initial Authentication & User Management
    auth_code_v1 = """import { db } from "../common/database";

export function login(email: string, passwordHash: string) {
    const user = db.query("SELECT * FROM users WHERE email = ?", [email]);
    if (!user) throw new Error("User not found");
    return { token: "jwt-token-sample", userId: user.id };
}

export function verifySession(token: string) {
    return token.startsWith("jwt-");
}
"""
    (src_dir / "auth" / "authService.ts").write_text(auth_code_v1, encoding="utf-8")

    db_code = """export const db = {
    query: (sql: string, params: any[]) => {
        return { id: "usr_101", email: "dev@archaeo.io", role: "admin" };
    }
};
"""
    (src_dir / "common" / "database.ts").write_text(db_code, encoding="utf-8")
    commit_with_date("feat: initial authentication and database connection module", "2022-04-10 10:14:00")

    # 2022-07-22: User Controller & Profile Service
    user_service_code = """import { login, verifySession } from "../auth/authService";
import { db } from "../common/database";

export class UserService {
    public authenticate(email: string, pass: string) {
        return login(email, pass);
    }

    public getUserProfile(userId: string) {
        return db.query("SELECT * FROM profiles WHERE id = ?", [userId]);
    }
}
"""
    (src_dir / "users" / "userService.ts").write_text(user_service_code, encoding="utf-8")

    user_controller_code = """import { UserService } from "./userService";

const userService = new UserService();

export function handleLoginRequest(req: any, res: any) {
    const { email, password } = req.body;
    const session = userService.authenticate(email, password);
    res.json(session);
}

export function handleProfileRequest(req: any, res: any) {
    const profile = userService.getUserProfile(req.params.id);
    res.json(profile);
}
"""
    (src_dir / "users" / "userController.ts").write_text(user_controller_code, encoding="utf-8")
    commit_with_date("feat: introduce UserService and UserController endpoints", "2022-07-22 14:30:00")

    # 2023-04-17: Payment Service creation & Stripe integration
    payment_service_code = """import { db } from "../common/database";
import { UserService } from "../users/userService";

const userService = new UserService();

export class PaymentService {
    public processStripePayment(userId: string, amount: number, currency: string) {
        const profile = userService.getUserProfile(userId);
        db.query("INSERT INTO transactions VALUES (?, ?, ?)", [userId, amount, currency]);
        return { status: "succeeded", transactionId: "txn_stripe_992" };
    }

    public refundPayment(transactionId: string) {
        return { status: "refunded", transactionId };
    }
}
"""
    (src_dir / "payment" / "paymentService.ts").write_text(payment_service_code, encoding="utf-8")

    payment_controller_code = """import { PaymentService } from "./paymentService";

const paymentService = new PaymentService();

export function processCheckout(req: any, res: any) {
    const result = paymentService.processStripePayment(req.body.userId, req.body.amount, "USD");
    res.json(result);
}
"""
    (src_dir / "payment" / "paymentController.ts").write_text(payment_controller_code, encoding="utf-8")
    commit_with_date("feat: introduce PaymentService with Stripe integration", "2023-04-17 09:20:00", "Marcus Vance", "marcus@archaeo.io")

    # 2023-08-11: Order Service dependent on Payment and User
    order_service_code = """import { PaymentService } from "../payment/paymentService";
import { UserService } from "../users/userService";

const paymentService = new PaymentService();
const userService = new UserService();

export class OrderService {
    public placeOrder(userId: string, items: any[]) {
        const user = userService.getUserProfile(userId);
        const total = items.reduce((acc, item) => acc + item.price, 0);
        const payment = paymentService.processStripePayment(userId, total, "USD");
        return { orderId: "ord_5521", status: "confirmed", payment };
    }
}
"""
    (src_dir / "orders" / "orderService.ts").write_text(order_service_code, encoding="utf-8")
    commit_with_date("feat: introduce OrderService coordinating payments and users", "2023-08-11 16:45:00", "Marcus Vance")

    # 2023-11-05: Unit tests for Payment and Auth
    test_code = """import { PaymentService } from "../payment/paymentService";
import { UserService } from "../users/userService";

describe("Payment and User Service Integration", () => {
    it("should process valid transactions", () => {
        const ps = new PaymentService();
        const res = ps.processStripePayment("usr_101", 150, "USD");
        expect(res.status).toBe("succeeded");
    });
});
"""
    (src_dir / "tests" / "payment.test.ts").write_text(test_code, encoding="utf-8")
    commit_with_date("test: add integration test suite for payment and user flows", "2023-11-05 11:15:00")

    # 2024-03-12: Redis Caching Layer introduced
    redis_code = """export const redisClient = {
    cache: new Map<string, any>(),
    get(key: string) { return this.cache.get(key); },
    set(key: string, val: any, ttlSec: number = 3600) { this.cache.set(key, val); },
    del(key: string) { this.cache.delete(key); }
};
"""
    (src_dir / "common" / "redisClient.ts").write_text(redis_code, encoding="utf-8")

    session_service_code = """import { redisClient } from "../common/redisClient";

export class SessionService {
    public setSession(sessionId: string, userData: any) {
        redisClient.set(`session:${sessionId}`, userData, 7200);
    }

    public getSession(sessionId: string) {
        return redisClient.get(`session:${sessionId}`);
    }
}
"""
    (src_dir / "auth" / "sessionService.ts").write_text(session_service_code, encoding="utf-8")
    commit_with_date("feat: introduce Redis caching layer and SessionService for high throughput", "2024-03-12 15:10:00", "Amina Chen", "amina@archaeo.io")

    # 2024-06-13: Bug Fix for payment timeout
    payment_service_v2 = payment_service_code + """
    public handlePaymentTimeoutRetry(transactionId: string) {
        // Fix for bug: retry payment verification with exponential backoff
        return { status: "retried", transactionId, retryCount: 3 };
    }
"""
    (src_dir / "payment" / "paymentService.ts").write_text(payment_service_v2, encoding="utf-8")
    commit_with_date("fix: resolve payment gateway timeout under heavy loads", "2024-06-13 18:22:00", "Marcus Vance")

    # 2024-09-28: Performance optimization for Redis session lookups
    session_service_v2 = session_service_code + """
    public batchGetSessions(sessionIds: string[]) {
        // Performance optimization: pipelined Redis MGET
        return sessionIds.map(id => redisClient.get(`session:${id}`));
    }
"""
    (src_dir / "auth" / "sessionService.ts").write_text(session_service_v2, encoding="utf-8")
    commit_with_date("perf: optimize Redis session caching with multi-key batch pipeline", "2024-09-28 12:40:00", "Amina Chen")

    # 2025-02-14: Security patch in authentication
    auth_service_v2 = """import { db } from "../common/database";
import { redisClient } from "../common/redisClient";

export function login(email: string, passwordHash: string) {
    // SECURITY: sanitize input to prevent injection
    const cleanEmail = email.trim().toLowerCase();
    const user = db.query("SELECT * FROM users WHERE email = ?", [cleanEmail]);
    if (!user) throw new Error("User not found");
    const token = `jwt-sec-token-${Date.now()}`;
    redisClient.set(`token:${token}`, { userId: user.id }, 3600);
    return { token, userId: user.id };
}

export function verifySession(token: string) {
    return redisClient.get(`token:${token}`) !== undefined;
}
"""
    (src_dir / "auth" / "authService.ts").write_text(auth_service_v2, encoding="utf-8")
    commit_with_date("sec: patch token verification and sanitize login inputs", "2025-02-14 10:05:00", "Elena Rostova")

    # 2025-08-30: Refactor PaymentService and refund handling
    payment_service_v3 = payment_service_v2 + """
    public validateStripeWebhook(signature: string, payload: any) {
        // Refactored webhook handler with cryptographic signature verification
        return signature.length > 10;
    }
"""
    (src_dir / "payment" / "paymentService.ts").write_text(payment_service_v3, encoding="utf-8")
    commit_with_date("refactor: modernize payment webhook verification and refund flow", "2025-08-30 17:15:00", "Marcus Vance")

    # 2026-03-01: Modernization of Order Service and Blast Radius validation
    order_service_v2 = order_service_code + """
    public cancelOrder(orderId: string, userId: string) {
        paymentService.refundPayment(`txn_refund_${orderId}`);
        return { orderId, status: "cancelled" };
    }
"""
    (src_dir / "orders" / "orderService.ts").write_text(order_service_v2, encoding="utf-8")
    commit_with_date("feat: implement order cancellation with automated payment refund propagation", "2026-03-01 11:00:00")

    return str(repo_path)
