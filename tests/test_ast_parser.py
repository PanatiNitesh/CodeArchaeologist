import pytest
from backend.app.phase2_ast.parser import CodeASTParser

def test_python_native_ast_parser():
    parser = CodeASTParser()
    py_code = '''
import os
from math import sqrt, pi as PI

@decorator_a
@decorator_b(arg=1)
class PaymentProcessor:
    """Processes online payments."""
    def __init__(self, key: str):
        self.key = key
        self.connect_gateway()

    def connect_gateway(self):
        return os.getenv("GATEWAY_URL")

@app.post("/checkout")
async def checkout(order_id: str, amount: float):
    """Initiates checkout flow."""
    processor = PaymentProcessor("key")
    return processor.connect_gateway()
'''
    res = parser.parse_file("services/payment.py", py_code)
    
    assert res["path"] == "services/payment.py"
    assert res["loc"] > 0
    
    # Verify imports
    import_sources = [imp["source"] for imp in res["imports"]]
    assert "os" in import_sources
    assert "math" in import_sources
    
    # Verify classes
    assert len(res["classes"]) == 1
    cls = res["classes"][0]
    assert cls["name"] == "PaymentProcessor"
    assert "PaymentProcessor.__init__" in cls["methods"]
    assert "PaymentProcessor.connect_gateway" in cls["methods"]
    assert "Processes online payments." in cls["docstring"]
    
    # Verify functions
    assert len(res["functions"]) == 1
    fn = res["functions"][0]
    assert fn["name"] == "checkout"
    assert fn["kind"] == "async_function"
    assert "order_id" in fn["params"]
    assert "amount" in fn["params"]
    assert "Initiates checkout flow." in fn["docstring"]

def test_typescript_generics_and_decorators():
    parser = CodeASTParser()
    ts_code = '''
import type { Request, Response } from 'express';
import { 
  Injectable, 
  Logger 
} from '@nestjs/common';

@Injectable()
export class UserService<T extends BaseUser> {
  private logger = new Logger();

  @AuditLog()
  async findById<R extends UserResult>(id: string, options: QueryOptions): Promise<R> {
    this.logger.log("Finding user");
    return this.db.find(id);
  }
}

export function transformData<K extends string, V>(({ key, val }: KeyValPair<K, V>)): V {
  return val;
}

export default process.env.NODE_ENV === 'test' ? MockService : UserService;
'''
    res = parser.parse_file("src/services/userService.ts", ts_code)
    
    # Verify multi-line import with type stripping
    all_imported = [name for imp in res["imports"] for name in imp["imported_names"]]
    assert "Request" in all_imported
    assert "Response" in all_imported
    assert "Injectable" in all_imported
    
    # Verify generic class
    assert len(res["classes"]) == 1
    cls = res["classes"][0]
    assert cls["name"] == "UserService"
    assert any("findById" in m for m in cls["methods"])
    assert any("@Injectable" in d for d in cls["decorators"])
    
    # Verify generic function with destructured params
    assert len(res["functions"]) == 1
    fn = res["functions"][0]
    assert fn["name"] == "transformData"
    assert "key" in fn["params"]
    assert "val" in fn["params"]
    
    # Verify conditional export
    export_names = [e["name"] for e in res["exports"]]
    assert "MockService" in export_names
    assert "UserService" in export_names
